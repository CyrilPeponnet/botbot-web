# pylint: disable=W0212
import json
import logging
from datetime import datetime

from django.utils.timezone import utc
import re
import botbot_plugins.plugins
from botbot_plugins.base import PrivateMessage
from django.core.cache import cache
from django.conf import settings
from django.utils.importlib import import_module
from django_statsd.clients import statsd

from botbot.apps.bots import models as bots_models
from botbot.apps.plugins.utils import convert_nano_timestamp, log_on_error
from .plugin import RealPluginMixin


CACHE_TIMEOUT_2H = 7200
LOG = logging.getLogger('botbot.plugin_runner')


class Line(object):
    """
    All the methods and data necessary for a plugin to act on a line
    """
    def __init__(self, packet, app):
        self.full_text = packet['Content']
        self.text = packet['Content']
        self.user = packet['User']

        # Private attributes not accessible to external plugins
        self._chatbot_id = packet['ChatBotId']
        self._raw = packet['Raw']
        self._channel_name = packet['Channel'].strip()
        self._command = packet['Command']
        self._is_message = packet['Command'] == 'PRIVMSG'
        self._host = packet['Host']

        self._received = convert_nano_timestamp(packet['Received'])

        self.is_direct_message = self.check_direct_message()

    def is_valid(self):
        if self._chatbot and self._channel:
            return True
        return False

    @property
    def _chatbot(self):
        """Simple caching for ChatBot model"""
        if not hasattr(self, '_chatbot_cache'):
            cache_key = 'chatbot:{0}'.format(self._chatbot_id)
            chatbot = cache.get(cache_key)
            if not chatbot:
                try:
                    chatbot = bots_models.ChatBot.objects.get(
                        id=self._chatbot_id)
                except bots_models.ChatBot.DoesNotExist:
                    LOG.warn('Chatbot %s does not exist. Line dropped.',
                             self._chatbot_id)
                    return None
                cache.set(cache_key, chatbot, CACHE_TIMEOUT_2H)
            self._chatbot_cache = chatbot
        return self._chatbot_cache

    @property
    def _channel(self):
        """Simple caching for Channel model"""
        if not hasattr(self, '_channel_cache'):
            cache_key = 'channel:{0}-{1}'.format(self._chatbot_id, self._channel_name)
            channel = cache.get(cache_key)

            if not channel and self._channel_name.startswith("#"):
                try:
                    channel = self._chatbot.channel_set.get(
                        name=self._channel_name)
                except self._chatbot.channel_set.model.DoesNotExist:
                    LOG.warn('Chatbot %s should not be listening to %s. '
                             'Line dropped.',
                             self._chatbot_id, self._channel_name)
                    return None
                cache.set(cache_key, channel, CACHE_TIMEOUT_2H)

                """
                The following logging is to help out in sentry. For some
                channels, we are getting occasional issues with the
                ``channel_set.get()`` lookup above
                """
                LOG.debug(channel)
                LOG.debug(self._channel_name)
                LOG.debug(cache_key)
                LOG.debug("%s", ", ".join(self._chatbot.channel_set.values_list('name', flat=True)))

            self._channel_cache = channel
        return self._channel_cache

    @property
    def _active_plugin_slugs(self):
        if not hasattr(self, '_active_plugin_slugs_cache'):
            if self._channel:
                self._active_plugin_slugs_cache = self._channel.active_plugin_slugs
            else:
                self._active_plugin_slugs_cache = set()
        return self._active_plugin_slugs_cache

    def check_direct_message(self):
        """
        If message is addressed to the bot, strip the bot's nick
        and return the rest of the message. Otherwise, return False.
        """

        nick = self._chatbot.nick

        # Private message
        if self._channel_name == nick:
            LOG.debug('Private message detected')
            # Set channel as user, so plugins reply by PM to correct user
            self._channel_name = self.user

            return True

        if len(nick) == 1:
            # support @<plugin> or !<plugin>
            regex = ur'^{0}(.*)'.format(re.escape(nick))
        else:
            # support <nick>: <plugin>
            regex = ur'^{0}[:\s](.*)'.format(re.escape(nick))
        match = re.match(regex, self.full_text, re.IGNORECASE)
        if match:
            LOG.debug('Direct message detected')
            self.text = match.groups()[0].lstrip()
            return True
        return False

    def __str__(self):
        return self.full_text

    def __repr__(self):
        return str(self)

def start_plugins(*args, **kwargs):
    """
    Used by the management command to start-up plugin listener
    and register the plugins.
    """
    pass
