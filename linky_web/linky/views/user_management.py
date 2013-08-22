import logging

from linky.forms import user_reg_form, regisrtar_member_form, registrar_form, journal_manager_form, journal_manager_form_edit, journal_member_form, journal_member_form_edit, regisrtar_member_form_edit, user_form_self_edit
from linky.models import Registrar, Link
from linky.utils import base

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import get_current_site
from django.utils.http import is_safe_url
from django.http import  HttpResponseRedirect
from django.template.response import TemplateResponse
from django.shortcuts import render_to_response, get_object_or_404, resolve_url
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.contrib import auth
from django.contrib.auth.models import User, Permission, Group
import random, string, smtplib
from email.mime.text import MIMEText
from django.core.paginator import Paginator
from linky.models import LinkUser
from ratelimit.decorators import ratelimit


logger = logging.getLogger(__name__)

try:
    from linky.local_settings import *
except ImportError, e:
    logger.error('Unable to load local_settings.py: %s', e)

@login_required
def landing(request):
    """ The logged-in user's dashboard. """
    # TODO: do we need this? We were using this, but it's need has
    # vanished since we moved the admin panel to the left column (on all admin pages)

    context = {'user': request.user}

    return render_to_response('user_management/landing.html', context)

@login_required
def manage_members(request):
    """ registry and registrar members can manage journal members (the folks that vest links) """

    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    context = {'user': request.user, 'registrar_members': list(registrars),
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = regisrtar_member_form(request.POST, prefix = "a")

        if form.is_valid():
            new_user = form.save()

            new_user.backend='django.contrib.auth.backends.ModelBackend'

            group = Group.objects.get(name='registrar_member')
            group.user_set.add(new_user)

            return HttpResponseRedirect(reverse('user_management_manage_registrar_member'))

        else:
            context.update({'regisrtar_register_form': form,})
    else:
        form = regisrtar_member_form(prefix = "a")
        context.update({'regisrtar_register_form': form,})

    return render_to_response('user_management/manage_registrar_members.html', context)

@login_required
def manage_registrar(request):
    """ Linky admins can manage registrars (libraries) """

    if request.user.groups.all()[0].name not in ['registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    # TODO: support paging at some point
    registrars = Registrar.objects.all()[:500]

    context = {'user': request.user, 'registrars': list(registrars),
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = registrar_form(request.POST, prefix = "a")

        if form.is_valid():
            new_user = form.save()

            return HttpResponseRedirect(reverse('user_management_manage_registrar'))

        else:
            context.update({'form': form,})
    else:
        form = registrar_form(prefix = "a")
        context.update({'form': form,})

    return render_to_response('user_management/manage_registrars.html', context)

@login_required
def manage_single_registrar(request, registrar_id):
    """ Linky admins can manage registrars (libraries)
        in this view, we allow for edit/delete"""

    if request.user.groups.all()[0].name not in ['registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    target_registrar = get_object_or_404(Registrar, id=registrar_id)

    context = {'user': request.user, 'target_registrar': target_registrar,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = registrar_form(request.POST, prefix = "a", instance=target_registrar)

        if form.is_valid():
            new_user = form.save()

            return HttpResponseRedirect(reverse('user_management_manage_registrar'))

        else:
            context.update({'form': form,})
    else:
        form = registrar_form(prefix = "a", instance=target_registrar)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_registrar.html', context)

@login_required
def manage_registrar_member(request):
    """ Linky admins can manage registrar members (librarians) """

    if request.user.groups.all()[0].name not in ['registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    registrar_members = LinkUser.objects.filter(groups__name='registrar_member', is_active=True)

    context = {'user': request.user, 'registrar_members': list(registrar_members),
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = regisrtar_member_form(request.POST, prefix = "a")

        if form.is_valid():
            new_user = form.save()

            new_user.backend='django.contrib.auth.backends.ModelBackend'
            
            group = Group.objects.get(name='registrar_member')
            new_user.groups.add(group)

            return HttpResponseRedirect(reverse('user_management_manage_registrar_member'))

        else:
            context.update({'form': form,})
    else:
        form = regisrtar_member_form(prefix = "a")
        context.update({'form': form,})

    return render_to_response('user_management/manage_registrar_members.html', context)

@login_required
def manage_single_registrar_member(request, user_id):
    """ Linky admins can manage registrar members (librarians)
        in this view, we allow for edit"""

    if request.user.groups.all()[0].name not in ['registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    target_registrar_member = get_object_or_404(LinkUser, id=user_id)

    context = {'user': request.user, 'target_registrar_member': target_registrar_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = regisrtar_member_form_edit(request.POST, prefix = "a", instance=target_registrar_member)

        if form.is_valid():
            new_user = form.save()

            return HttpResponseRedirect(reverse('user_management_manage_registrar_member'))

        else:
            context.update({'form': form,})
    else:
        form = regisrtar_member_form_edit(prefix = "a", instance=target_registrar_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_registrar_member.html', context)

@login_required
def manage_single_registrar_member_delete(request, user_id):
    """ Linky admins can manage registrar members. Delete a single registrar member here. """

    # Only registry members can delete registrar members
    if request.user.groups.all()[0].name not in ['registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    target_member = get_object_or_404(LinkUser, id=user_id)

    context = {'user': request.user, 'target_member': target_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':
        target_member.is_active = False
        target_member.save()

        return HttpResponseRedirect(reverse('user_management_manage_registrar_member'))
    else:
        form = journal_member_form_edit(prefix = "a", instance=target_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_registrar_member_delete_confirm.html', context)

@login_required
def manage_journal_manager(request):
    """ Linky admins and registrars can manage journal members """

    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    # If registry member, return all active journal members. If registrar member, return just those journal members that belong to the registrar member's registrar
    if request.user.groups.all()[0].name == 'registry_member':
        journal_managers = LinkUser.objects.filter(groups__name='journal_manager', is_active=True)
    else:
        journal_managers = LinkUser.objects.filter(groups__name='journal_manager', registrar=request.user.registrar, is_active=True).exclude(id=request.user.id)

    context = {'user': request.user, 'journal_managers': list(journal_managers),
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = journal_manager_form(request.POST, prefix = "a")

        if form.is_valid():
            new_user = form.save()

            new_user.backend='django.contrib.auth.backends.ModelBackend'
            
            new_user.registrar = request.user.registrar
            new_user.save()

            group = Group.objects.get(name='journal_manager')
            new_user.groups.add(group)

            return HttpResponseRedirect(reverse('user_management_manage_journal_manager'))

        else:
            context.update({'form': form,})
    else:
        form = journal_manager_form(prefix = "a")
        context.update({'form': form,})

    return render_to_response('user_management/manage_journal_managers.html', context)

@login_required
def manage_single_journal_manager(request, user_id):
    """ Linky admins and registrars can manage journal members. Edit a single journal member here. """

    # Only registry members and registrar memebers can edit journal members
    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member']:
        return HttpResponseRedirect(reverse('user_management_created_links'))

    target_member = get_object_or_404(LinkUser, id=user_id)

    # Registrar members can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member']:
        if request.user.registrar != target_member.registrar:
            return HttpResponseRedirect(reverse('user_management_created_links'))

    context = {'user': request.user, 'target_member': target_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = journal_manager_form_edit(request.POST, prefix = "a", instance=target_member)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse('user_management_manage_journal_manager'))

        else:
            context.update({'form': form,})
    else:
        form = journal_manager_form_edit(prefix = "a", instance=target_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_journal_manager.html', context)

@login_required
def manage_single_journal_manager_delete(request, user_id):
    """ Linky admins and registrars can manage journal members. Delete a single journal member here. """

    # Only registry members and registrar memebers can edit journal managers
    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    target_member = get_object_or_404(LinkUser, id=user_id)

    # Registrar members can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member']:
        if request.user.registrar != target_member.registrar:
            return HttpResponseRedirect(reverse('user_management_landing'))

    context = {'user': request.user, 'target_member': target_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':
        target_member.is_active = False
        target_member.save()

        return HttpResponseRedirect(reverse('user_management_manage_journal_manager'))
    else:
        form = journal_manager_form_edit(prefix = "a", instance=target_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_journal_manager_delete_confirm.html', context)

valid_sorts = ['-creation_timestamp', 'creation_timestamp', 'vested_timestamp', '-vested_timestamp']

@login_required
def manage_journal_member(request):
    """ Linky admins and registrars can manage journal members """

    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member', 'journal_manager']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    # If registry member, return all active journal members. If registrar member, return just those journal members that belong to the registrar member's registrar
    if request.user.groups.all()[0].name == 'registry_member':
        journal_members = LinkUser.objects.filter(groups__name='journal_member', is_active=True)
    elif request.user.groups.all()[0].name == 'journal_manager':
        journal_members = LinkUser.objects.filter(authorized_by=request.user, is_active=True).exclude(id=request.user.id)
    else:
        journal_members = LinkUser.objects.filter(groups__name='journal_member', registrar=request.user.registrar, is_active=True).exclude(id=request.user.id)

    context = {'user': request.user, 'journal_members': list(journal_members),
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = journal_member_form(request.POST, prefix = "a")

        if form.is_valid():
            new_user = form.save()

            new_user.backend='django.contrib.auth.backends.ModelBackend'
            
            new_user.registrar = request.user.registrar
            new_user.authorized_by = request.user
            new_user.save()

            group = Group.objects.get(name='journal_member')
            new_user.groups.add(group)

            return HttpResponseRedirect(reverse('user_management_manage_journal_member'))

        else:
            context.update({'form': form,})
    else:
        form = journal_member_form(prefix = "a")
        context.update({'form': form,})

    return render_to_response('user_management/manage_journal_members.html', context)

@login_required
def manage_single_journal_member(request, user_id):
    """ Linky admins and registrars can manage journal members. Edit a single journal member here. """

    # Only registry members and registrar memebers can edit journal members
    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member', 'journal_manager']:
        return HttpResponseRedirect(reverse('user_management_created_links'))

    target_member = get_object_or_404(LinkUser, id=user_id)

    # Registrar members can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member']:
        if request.user.registrar != target_member.registrar:
            return HttpResponseRedirect(reverse('user_management_created_links'))
            
    # Journal managers can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member', 'registrar_member']:
        if request.user != target_member.authorized_by:
            return HttpResponseRedirect(reverse('user_management_created_links'))


    context = {'user': request.user, 'target_member': target_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':

        form = journal_member_form_edit(request.POST, prefix = "a", instance=target_member)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse('user_management_manage_journal_member'))

        else:
            context.update({'form': form,})
    else:
        form = journal_member_form_edit(prefix = "a", instance=target_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_journal_member.html', context)

@login_required
def manage_single_journal_member_delete(request, user_id):
    """ Linky admins and registrars can manage journal members. Delete a single journal member here. """

    # Only registry members and registrar memebers can edit journal members
    if request.user.groups.all()[0].name not in ['registrar_member', 'registry_member', 'journal_manager']:
        return HttpResponseRedirect(reverse('user_management_landing'))

    target_member = get_object_or_404(LinkUser, id=user_id)

    # Registrar members can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member']:
        if request.user.registrar != target_member.registrar:
            return HttpResponseRedirect(reverse('user_management_landing'))
            
    # Journal managers can only edit their own journal members
    if request.user.groups.all()[0].name not in ['registry_member', 'registrar_member']:
        if request.user != target_member.authorized_by:
            return HttpResponseRedirect(reverse('user_management_created_links'))

    context = {'user': request.user, 'target_member': target_member,
        'this_page': 'users'}
    context.update(csrf(request))

    if request.method == 'POST':
        target_member.is_active = False
        target_member.save()

        return HttpResponseRedirect(reverse('user_management_manage_journal_member'))
    else:
        form = journal_member_form_edit(prefix = "a", instance=target_member)
        context.update({'form': form,})

    return render_to_response('user_management/manage_single_journal_member_delete_confirm.html', context)

valid_sorts = ['-creation_timestamp', 'creation_timestamp', 'vested_timestamp', '-vested_timestamp']

@login_required
def created_links(request):
    """ Anyone with an account can view the linky links they've created """

    DEFAULT_SORT = '-creation_timestamp'

    sort = request.GET.get('sort', DEFAULT_SORT)
    if sort not in valid_sorts:
        sort = DEFAULT_SORT
    page = request.GET.get('page', 1)
    if page < 1:
        page = 1

    linky_links = Link.objects.filter(created_by=request.user).order_by(sort)
    total_created = len(linky_links)

    paginator = Paginator(linky_links, 10)
    linky_links = paginator.page(page)

    for linky_link in linky_links:
        #linky_link.id =  base.convert(linky_link.id, base.BASE10, base.BASE58)
        if len(linky_link.submitted_title) > 50:
          linky_link.submitted_title = linky_link.submitted_title[:50] + '...'
        if len(linky_link.submitted_url) > 79:
          linky_link.submitted_url = linky_link.submitted_url[:70] + '...'

    context = {'user': request.user, 'linky_links': linky_links, 'host': request.get_host(),
               'total_created': total_created, sort : sort, 'this_page': 'created_links'}

    return render_to_response('user_management/created-links.html', context)

@login_required
def vested_links(request):
    """ Linky admins and registrar members and journal members can vest link links """

    if request.user.groups.all()[0].name not in ['journal_member', 'registrar_member', 'registry_member']:
        return HttpResponseRedirect(reverse('user_management_landing'))
        
    
    DEFAULT_SORT = '-creation_timestamp'

    sort = request.GET.get('sort', DEFAULT_SORT)
    if sort not in valid_sorts:
        sort = DEFAULT_SORT
    page = request.GET.get('page', 1)
    if page < 1:
        page = 1

    linky_links = Link.objects.filter(vested_by_editor=request.user).order_by(sort)
    total_vested = len(linky_links)
    
    paginator = Paginator(linky_links, 10)
    linky_links = paginator.page(page)

    for linky_link in linky_links:
        #linky_link.id =  base.convert(linky_link.id, base.BASE10, base.BASE58)
        if len(linky_link.submitted_title) > 50:
          linky_link.submitted_title = linky_link.submitted_title[:50] + '...'
        if len(linky_link.submitted_url) > 79:
          linky_link.submitted_url = linky_link.submitted_url[:70] + '...'

    context = {'user': request.user, 'linky_links': linky_links, 'host': request.get_host(),
               'total_vested': total_vested, 'this_page': 'vested_links'}

    return render_to_response('user_management/vested-links.html', context)

@login_required
def manage_account(request):
    """ Account mangement stuff. Change password, change email, ... """

    context = {'host': request.get_host(), 'user': request.user,
        'next': request.get_full_path(), 'this_page': 'settings'}
    context.update(csrf(request))
    if request.user.groups.all()[0].name in ['journal_member', 'journal_manager']:
      context.update({'sponsoring_library_name': request.user.registrar.name, 'sponsoring_library_email': request.user.registrar.email, 'sponsoring_library_website': request.user.registrar.website})
    
    if request.method == 'POST':

        form = user_form_self_edit(request.POST, prefix = "a", instance=request.user)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse('user_management_manage_account'))

        else:
            context.update({'form': form,})
    else:
        form = user_form_self_edit(prefix = "a", instance=request.user)
        context.update({'form': form,})

    return render_to_response('user_management/manage-account.html', context)

@login_required
def batch_convert(request):
    """Detect and archive URLs from user input."""
    # TODO
    context = {'host': request.get_host(), 'user': request.user,
        'this_page': 'batch_convert'}
    context.update(csrf(request))
    return render_to_response('user_management/batch_convert.html', context)

@login_required
def export(request):
    """Export a CSV of a user's library."""
    # TODO
    context = {'host': request.get_host(), 'user': request.user,
        'this_page': 'export'}
    context.update(csrf(request))
    return render_to_response('user_management/export.html', context)

@login_required
def custom_domain(request):
    """Instructions for a user to configure a custom domain."""
    # TODO
    context = {'host': request.get_host(), 'user': request.user,
        'this_page': 'custom_domain'}
    context.update(csrf(request))
    return render_to_response('user_management/custom_domain.html', context)
    
@ratelimit(method='POST', rate=INTERNAL['LOGIN_MINUTE_LIMIT'], block='True', ip=True)
#@ratelimit(method='POST', rate=INTERNAL['LOGIN_HOUR_LIMIT'], block='True', ip=True)
#@ratelimit(method='POST', rate=INTERNAL['LOGIN_DAY_LIMIT'], block='True', ip=True)
def limited_login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    request.session.set_test_cookie()

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())

            return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)

@ratelimit(method='POST', rate=INTERNAL['REGISTER_MINUTE_LIMIT'], block='True')
@ratelimit(method='POST', rate=INTERNAL['REGISTER_HOUR_LIMIT'], block='True')
@ratelimit(method='POST', rate=INTERNAL['REGISTER_DAY_LIMIT'], block='True')
def process_register(request):
    """Register a new user"""
    c = {}
    c.update(csrf(request))

    if request.method == 'POST':

        reg_key = request.POST.get('reg_key', '')

        editor_reg_form = user_reg_form(request.POST, prefix = "a")

        if editor_reg_form.is_valid():
            new_user = editor_reg_form.save()

            new_user.backend='django.contrib.auth.backends.ModelBackend'
            
            new_user.is_active = False
            new_user.confirmation_code = \
                ''.join(random.choice(string.ascii_uppercase + \
                string.ascii_lowercase + string.digits) for x in range(30))
            new_user.save()
            
            from_address = "lil@law.harvard.edu"
            to_address = new_user.email
            content = '''To confirm your account, please click the link below or copy it to your web browser:

http://perma.law.harvard.edu/register/confirm/%s/

''' % new_user.confirmation_code
        
            msg = MIMEText(content)
            msg['Subject'] = "Perma account confirmation"
            msg['From'] = from_address
            msg['To'] = to_address
        
            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('localhost')
            s.sendmail(from_address, [to_address], msg.as_string())
            s.quit()


            group = Group.objects.get(name='user')
            new_user.groups.add(group)

            return HttpResponseRedirect(reverse('register_email_instructions'))

        else:
            c.update({'editor_reg_form': editor_reg_form,})

            return render_to_response('registration/register.html', c)
    else:
        editor_reg_form = user_reg_form (prefix = "a")

        c.update({'editor_reg_form': editor_reg_form,})
        return render_to_response("registration/register.html", c)
        
def register_email_code_confirmation(request, code):
    '''Confirm a user's account when the user follows the email confirmation 
    link.'''
    user = get_object_or_404(LinkUser, confirmation_code=code)
    user.is_active = True
    user.save()
    redirect_url = reverse('auth_login')
    extra_params = '?confirmed=true'
    full_redirect_url = '%s%s' % (redirect_url, extra_params)
    return HttpResponseRedirect(full_redirect_url)
    
def register_email_instructions(request):
    """After the user has registered, give the instructions for confirming"""
    return render_to_response('registration/check_email.html', {})