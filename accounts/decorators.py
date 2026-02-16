from django.shortcuts import redirect
from django.http import HttpResponseForbidden


def anonymous_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')  # hoặc dashboard theo vai trò
        return view_func(request, *args, **kwargs)
    return wrapper


# accounts/decorators.py


def role_required(*required_role):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in required_role:
                return HttpResponseForbidden("Không có quyền truy cập." + str(request.user.role))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
