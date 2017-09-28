from launchpad.views import Signup

from botbot.apps.bots import models as bots_models


class LandingPage(Signup):
    def get_context_data(self, **kwargs):
        kwargs.update({
            'public_channels': bots_models.Channel.objects \
                .filter(is_public=True).active() \
                .select_related('chatbot')
        })
        return kwargs
