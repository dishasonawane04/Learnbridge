#!/usr/bin/env python
"""
Comprehensive Platform Audit Script
Checks for common errors, broken links, and issues across the platform
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.conf import settings
from django.urls import get_resolver, URLPattern, URLResolver
from django.test import Client
from django.contrib.auth import get_user_model
import sys

def get_all_urls(resolver=None, prefix=''):
    """Recursively get all URL patterns"""
    if resolver is None:
        resolver = get_resolver()
    
    urls = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            urls.extend(get_all_urls(pattern, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            url_name = pattern.name
            url_pattern = prefix + str(pattern.pattern)
            urls.append((url_name, url_pattern))
    return urls

def audit_platform():
    """Run comprehensive platform audit"""
    print("=" * 80)
    print("LEARNBRIDGE PLATFORM AUDIT")
    print("=" * 80)
    
    # 1. Check installed apps
    print("\n📦 INSTALLED APPS:")
    print("-" * 80)
    for app in settings.INSTALLED_APPS:
        if not app.startswith('django.'):
            print(f"  ✓ {app}")
    
    # 2. Check URL patterns
    print("\n🔗 URL PATTERNS AUDIT:")
    print("-" * 80)
    urls = get_all_urls()
    print(f"  Total URL patterns: {len(urls)}")
    
    # Group by app
    url_by_app = {}
    for name, pattern in urls:
        if name:
            app = name.split(':')[0] if ':' in name else 'core'
            if app not in url_by_app:
                url_by_app[app] = []
            url_by_app[app].append(name)
    
    for app, app_urls in sorted(url_by_app.items()):
        print(f"\n  {app}: {len(app_urls)} URLs")
        for url in sorted(app_urls)[:5]:  # Show first 5
            print(f"    - {url}")
        if len(app_urls) > 5:
            print(f"    ... and {len(app_urls) - 5} more")
    
    # 3. Test critical pages
    print("\n🧪 TESTING CRITICAL PAGES:")
    print("-" * 80)
    
    User = get_user_model()
    settings.ALLOWED_HOSTS += ['testserver']
    
    # Get or create test user
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@test.com', 'admin')
    
    client = Client()
    client.force_login(user)
    
    critical_urls = [
        ('home', '/'),
        ('course:list', None),
        ('accounts:login', None),
        ('accounts:signup', None),
    ]
    
    for url_name, url_path in critical_urls:
        try:
            if url_path:
                response = client.get(url_path)
            else:
                from django.urls import reverse
                response = client.get(reverse(url_name))
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"  {status} {url_name}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {url_name}: ERROR - {str(e)[:60]}")
    
    # 4. Check for common issues
    print("\n⚠️  COMMON ISSUES CHECK:")
    print("-" * 80)
    
    issues = []
    
    # Check SECRET_KEY
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 50:
        issues.append("SECRET_KEY is too short or missing")
    
    # Check DEBUG
    if settings.DEBUG:
        issues.append("DEBUG is True (should be False in production)")
    
    # Check ALLOWED_HOSTS
    if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ['*']:
        issues.append("ALLOWED_HOSTS not properly configured")
    
    # Check STATIC/MEDIA
    if not hasattr(settings, 'STATIC_ROOT') or not settings.STATIC_ROOT:
        issues.append("STATIC_ROOT not configured")
    
    if issues:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ No common configuration issues found")
    
    # 5. Database check
    print("\n💾 DATABASE CHECK:")
    print("-" * 80)
    from course.models import Course, CourseUnit
    from django.contrib.auth.models import User
    
    print(f"  Users: {User.objects.count()}")
    print(f"  Courses: {Course.objects.count()}")
    print(f"  Units: {CourseUnit.objects.count()}")
    
    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    audit_platform()
