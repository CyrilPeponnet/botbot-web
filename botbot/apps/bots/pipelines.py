from botbot.apps.accounts import models as account_models
from django.contrib.auth import login
from django_slack_oauth.models import SlackUser


def register_user(request, api_data):
    user, _ = account_models.User.objects.get_or_create(username=api_data['user_id'])

    slacker, _ = SlackUser.objects.get_or_create(slacker=user)
    slacker.access_token = api_data.pop('access_token')
    slacker.extras = api_data
    slacker.save()

    request.created_user = user

    return request, api_data


def debug_oauth_request(request, api_data):
    print(api_data)
    return request, api_data


def log_user_in(request, api_data):
    user = account_models.User.objects.get(username=api_data['user_id'])
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    return request, api_data
