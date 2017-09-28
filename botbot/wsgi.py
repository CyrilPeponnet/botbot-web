import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "botbot.settings")
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
application = get_wsgi_application()
application = DjangoWhiteNoise(application)
