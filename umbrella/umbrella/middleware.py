from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from umbrella_logger import logger


class SetNextParameterMiddleware(MiddlewareMixin):
    """
        Middleware to redirect unauthenticated users accessing the /custom_page/ endpoint
        Custom_page is our predefined workflow page

        This middleware checks if the user is trying to access the /umbrella/ endpoint
        and is not authenticated. If so, it redirects the user to the login page
        with the `next` parameter set to a custom page URL
        Note(Yongbaek):
        This middleware class intercept the request from the user, and it redirects to the speicifc
        webpage. This is not an ideal case, but we should create new FE webpage separately in the future.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        custom_page_url = reverse('custom:custom')
        admin = reverse('admin:index')
        # Print debug information
        logger.debug(f'Request Path: {request.path}')
        logger.debug(f'custom page url: {custom_page_url}')
        logger.debug(f'Request GET parameters: {request.GET}')
        logger.debug(f'Admin index URL: {admin}')
        logger.debug(f'Is user authenticated: {request.user.is_authenticated}')

        # Check if the user is authenticated and trying to access /umbrella/
        if request.path == custom_page_url or request.path == '/admin/login/':
            if not request.user.is_authenticated:
                # Redirect to login page with next parameter set to custom_page
                next_param = request.GET.get('next', '')
                if next_param != custom_page_url:
                    login_url = reverse('login')
                    redirect_url = f'{login_url}?next={custom_page_url}'
                    logger.info('Redirecting to login with next parameter set to custom_page')
                    return redirect(redirect_url)
            # If authenticated, proceed to the original umbrella page
            else:
                return None


