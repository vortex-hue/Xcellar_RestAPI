class ProxyMiddleware:
    """
    Middleware to extract the real client IP from HTTP_X_FORWARDED_FOR header.
    Essential for applications running behind a load balancer (like Render).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # The first IP in the list is the client's real IP
            ip = x_forwarded_for.split(',')[0].strip()
            request.META['REMOTE_ADDR'] = ip
        return self.get_response(request)
