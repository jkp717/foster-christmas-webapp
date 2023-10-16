from sqlalchemy.exc import IntegrityError
from flask import flash, request, redirect
from markupsafe import Markup
from flask_admin import expose, BaseView, AdminIndexView
from flask_admin.actions import action
from flask_admin.babel import ngettext
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.contrib.sqla import ModelView
from flask_admin.babel import gettext
from flask_admin.form import rules, FormOpts
from wtforms_alchemy import PhoneNumberField
from flask_admin.contrib.sqla.filters import FilterLike, FilterEqual, BooleanEqualFilter

from webapp.models import db, Gift, Child, Parent, DhsOffice, Gender, Race, ShoeSize, ClothingSize, FavColor, \
    Church, Sponsor, SponsorRequest
import webapp.util as util
from webapp.config import GIFT_DELIVERY_DISCLAIMER, REGISTER_CHILD_DISCLAIMER, SPONSORSHIP_DISCLAIMER, \
    SPONSOR_CHILD_DISCLAIMER, SPONSOR_REQUEST_DISCLAIMER


class IndexView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render(
            'main/index.html',
        )


class RegisterView(BaseView):
    can_create = True  # Sets if 'add another' option is present
    _raised_integrity_error = False  # flag if unique constraint fails

    def handle_integrity_error(self, exc):
        if isinstance(exc, IntegrityError):
            self._raised_integrity_error = True
            return True
        return False

    @expose('/', methods=['GET', 'POST'])
    def parent(self):
        model_view = ParentView(Parent, db.session)
        return_url = '/'
        id = get_mdict_item_or_list(request.args, 'id')
        if id is not None:
            model = model_view.get_one(id)
            if model is None:
                flash(gettext('Parent record does not exist.'), 'error')
                return redirect(return_url)
            form = model_view.edit_form(obj=model)
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_edit_rules  # noqa
            )
            if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:  # noqa
                model_view._validate_form_instance(ruleset=model_view._form_edit_rules, form=form)  # noqa
            if model_view.validate_form(form):
                if model_view.update_model(form, model):
                    flash(gettext('Record was successfully updated.'), 'success')
                    return redirect(self.get_url('register.child', parent_id=model.id))
            if request.method == 'GET' or form.errors:
                model_view.on_form_prefill(form, id)
        else:
            form = model_view.create_form()
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_create_rules  # noqa
            )
            if model_view.validate_form(form):
                model_view.handle_view_exception = self.handle_integrity_error
                model = model_view.create_model(form)
                if self._raised_integrity_error:
                    model = db.session.query(Parent).filter(
                        Parent.first_name == form.first_name.data.title(),
                        Parent.last_name == form.last_name.data.title(),
                        Parent.email == form.email.data.lower(),
                    ).first()
                if model:
                    # flash(gettext('Your information has been saved! '), 'success')
                    return redirect(self.get_url('register.child', parent_id=model.id))
        return self.render(
            'main/register.html',
            form=form,
            form_opts=form_opts,
            submit_text='Add Children',
            return_url='/',
        )

    @expose('/<int:parent_id>/child', methods=['GET', 'POST'])
    def child(self, parent_id):
        parent = db.session.query(Parent).filter(Parent.id == parent_id).one()
        if not parent:
            flash("Unable to find the foster parent information in system!")
            return redirect('/')
        model_view = ChildView(Child, db.session)
        id = get_mdict_item_or_list(request.args, 'id')
        if id is not None:
            model = model_view.get_one(id)
            if model is None:
                flash(gettext('Child record does not exist.'), 'error')
                return redirect(self.get_url('register.child', parent_id=parent_id))
            if request.args.get('delete'):
                db.session.delete(model)
                db.session.commit()
                flash(gettext('Child record has been deleted.'), 'success')
                return redirect(self.get_url('register.child', parent_id=parent_id))
            form = model_view.edit_form(obj=model)
            form.parent.data = parent
            form.parent.render_kw = {'disabled': ''}
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_edit_rules  # noqa
            )
            if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:  # noqa
                model_view._validate_form_instance(ruleset=model_view._form_edit_rules, form=form)  # noqa
            if model_view.validate_form(form):
                if model_view.update_model(form, model):
                    flash(gettext('Child was successfully added.'), 'success')
                    if '_add_another' in request.form:
                        return redirect(self.get_url('register.child', parent_id=parent_id))
                    return redirect('/')
            if request.method == 'GET' or form.errors:
                model_view.on_form_prefill(form, id)
        else:
            form = model_view.create_form()
            if hasattr(form, 'parent'):
                form.parent.data = parent
                form.parent.render_kw = {'disabled': ''}
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_create_rules  # noqa
            )
            if model_view.validate_form(form):
                model = model_view.create_model(form)
                if model:
                    if '_add_another' in request.form:
                        flash(gettext('Our records have been updated! Add another child or click finish.'), 'success')
                        return redirect(self.get_url('register.child', parent_id=parent_id))
                    flash("Your children have been registered! Thank you!")
                    return redirect('/')
        flash(Markup(Markup(REGISTER_CHILD_DISCLAIMER)))
        return self.render(
            'main/register.html',
            form=form,
            form_opts=form_opts,
            submit_text='Finish',
            return_url='/',
            add_another=True,
            parent=parent
        )

    @expose('/sponsor', methods=['GET', 'POST'])
    def sponsor(self):
        model_view = SponsorView(Sponsor, db.session)
        return_url = '/'
        id = get_mdict_item_or_list(request.args, 'id')
        if id is not None:
            model = model_view.get_one(id)
            if model is None:
                flash(gettext('Sponsor record does not exist.'), 'error')
                return redirect(return_url)
            form = model_view.edit_form(obj=model)
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_edit_rules  # noqa
            )
            if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:  # noqa
                model_view._validate_form_instance(ruleset=model_view._form_edit_rules, form=form)  # noqa
            if model_view.validate_form(form):
                if model_view.update_model(form, model):
                    flash(gettext('Thank you for your sponsorship!'), 'success')
                    return redirect('/')
            if request.method == 'GET' or form.errors:
                model_view.on_form_prefill(form, id)
        else:
            form = model_view.create_form()
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_create_rules  # noqa
            )
            if model_view.validate_form(form):
                model_view.handle_view_exception = self.handle_integrity_error
                model = model_view.create_model(form)
                if model:
                    flash(gettext('Thank you for your sponsorship!'), 'success')
                    return redirect('/')
                else:
                    if request.method == 'GET' or form.errors:
                        model_view.on_form_prefill(form, id)
        flash(Markup(Markup(SPONSORSHIP_DISCLAIMER)))
        return self.render(
            'main/sponsor.html',
            form=form,
            form_opts=form_opts,
            return_url='/',
        )

    @expose('/sponsor-request', methods=['GET', 'POST'])
    def sponsor_request(self):
        model_view = SponsorRequestView(SponsorRequest, db.session)
        # return_url = '/'
        form = model_view.create_form()
        form_opts = FormOpts(
            widget_args=model_view.form_widget_args,
            form_rules=model_view._form_create_rules  # noqa
        )
        if model_view.validate_form(form):
            model_view.handle_view_exception = self.handle_integrity_error
            model = model_view.create_model(form)
            if model:
                flash(gettext('Thank you for your sponsorship!'), 'success')
                flash(Markup(SPONSOR_REQUEST_DISCLAIMER), 'success')
                return redirect('/')
            else:
                if request.method == 'GET' or form.errors:
                    model_view.on_form_prefill(form, id)
        return self.render(
            'main/sponsor-request.html',
            form=form,
            form_opts=form_opts,
            return_url='/',
        )

    @expose('/get-involved', methods=['GET'])
    def get_involved(self):
        return self.render(
            'main/get-involved.html',
        )

    @expose('/details', methods=['GET'])
    def details(self):
        return self.render(
            'main/details.html',
        )

    def is_visible(self):
        return False


class AdminReportsView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render(
            'admin/index.html',
        )

    @expose('/download/<report_name>')
    def download(self, report_name):
        if report_name.upper() == 'ALL_SPONSORED':
            return redirect(self.get_url('admin.child', flt1_sponsored_equals=1))


class BaseView(ModelView):
    column_type_formatters = util.DEFAULT_FORMATTERS
    form_excluded_columns = ['create_date', 'modify_date']
    column_exclude_list = form_excluded_columns
    # column_type_formatters = utils.get_config_formatters()
    named_filter_urls = True
    can_view_details = True
    can_edit = True
    can_export = True
    can_delete = True
    can_create = True
    edit_template = 'admin/edit.html'
    create_template = 'admin/create.html'


class ChildView(BaseView):
    column_list = [
        'id', 'parent', 'first_name', 'last_name', 'dhs_office', 'age', 'dhs_case_worker', 'gender',
        'has_sponsor', 'gifts', 'church', 'note'
    ]
    form_exclude_columns = [
        'id', 'church', 'note', 'has_sponsor'
    ]
    column_editable_list = ['church', 'note']
    column_descriptions = {
        "church": "Church given child's gift registration (if applicable)",
        "has_sponsor": "If a sponsor has been assigned to this child",
        "gifts": "Count of gifts registered (click link to see gifts)",
        
    }
    column_sortable_list = [
        ('parent', 'parent.last_name'), 'first_name', 'last_name', 'dhs_case_worker',
        ('dhs_office', 'dhs_office.office'), 'age', ('race', 'race.race'), ('gender', 'gender.gender'),
        ('fav_color', 'fav_color.color'), ('shoe_size', 'shoe_size.size'), ('clothing_size', 'clothing_size.size'),
        ('church', 'church.church'), 'has_sponsor'
    ]
    column_filters = [
        'id',
        'age',
        BooleanEqualFilter('has_sponsor', 'Sponsored'),
        FilterLike(Parent.last_name, 'Parent Last Name'),
        FilterLike(Parent.first_name, 'Parent First Name'),
        FilterLike('dhs_case_worker', 'Case Worker'),
        FilterLike('first_name', 'Child First Name'),
        FilterLike('last_name', 'Child Last Name'),
        FilterEqual(DhsOffice.office, 'DHS Office', options=util.get_dhs_office_options),
        FilterEqual(Race.race, 'Child Race', options=util.get_race_options),
        FilterEqual(Gender.gender, 'Child Gender', options=util.get_gender_options),
        FilterEqual(ShoeSize.size, 'Shoe Size', options=util.get_shoe_size_options),
        FilterEqual(ClothingSize.size, 'Clothing Size', options=util.get_clothing_size_options),
        FilterEqual(FavColor.color, 'Favorite Color', options=util.get_fav_color_options),
        FilterEqual(Church.church, 'Assigned Church', options=util.get_church_options)
    ]
    column_searchable_list = [Gift.gift]
    form_rules = [
        rules.NestedRule([rules.Header('Foster Parent'), 'parent', rules.Macro('render_child_list')]),
        rules.NestedRule([
            rules.Header('Add Foster Child'), 'first_name', 'last_name', 'dhs_case_worker',
            'dhs_office', 'age', 'race', 'gender', 'fav_color', 'shoe_size', 'clothing_size'
        ]),
        rules.NestedRule([
            'gifts',
            rules.Macro('form_helper_text', msg="Please limit to 5 gifts per child"),
            rules.Macro('form_helper_text', msg="Please refrain from including electronics exceeding a value of $200."),
        ])
    ]
    inline_models = [(Gift, dict(form_columns=['id', 'gift']))]
    column_labels = {
        'dhs_case_worker': 'Case Worker',
        'dhs_office': 'DHS Office',
        'fav_color': 'Fav. Color',
        'parent': 'Foster Parent',
        'note': 'Notes',
        'has_sponsor': 'Sponsored'
    }
    column_formatters = {
        'gifts': util.gift_list_formatter
    }
    column_formatters_export = {
        'gifts': util.gift_list_export_formatter
    }

    @expose('/')
    def index_view(self):
        self._refresh_filters_cache()
        return super(ChildView, self).index_view()


class ParentView(BaseView):
    form_columns = ['first_name', 'last_name', 'phone', 'email', 'gift_delivery']
    form_rules = {
        rules.NestedRule([
            rules.NestedRule(
                [rules.Header('Foster Parent'), 'first_name', 'last_name', 'phone', 'email']
            ),
            rules.NestedRule(
                [rules.HTML(f"""<small class="form-text text-muted">{GIFT_DELIVERY_DISCLAIMER}</small>"""),
                 'gift_delivery']
            )
        ])
    }
    column_labels = {
        'gift_delivery': 'DHS Delivery'
    }
    form_overrides = {
        'phone': PhoneNumberField,
    }


class GiftView(BaseView):
    column_display_pk = True
    column_filters = ['child_id', 'child', 'create_date', 'received']
    column_searchable_list = ['gift']
    column_sortable_list = {('child', 'child.last_name'), 'create_date', 'gift', 'received'}
    column_list = ('id', 'gift.create_date', 'child', 'received', 'gift')
    column_export_list = [
        'child_id', 'child.last_name', 'child.first_name', 'child.age', 'child.gender', 'gift', 'child.sponsor',
        'received', 'create_date'
    ]
    column_labels = {
        'child.last_name': 'Child Last',
        'child.first_name': 'Child First',
        'child.age': 'Age',
        'child.fav_color': 'Fav Color',
        'child.shoe_size': 'Shoe Size',
        'child.clothing_size': 'Clothing Size',
        'child.gender': 'Gender',
        'child.sponsor': 'Sponsor',
        'create_date': 'Registered Date'
    }

    @action('receive_gift', 'Mark as Received', 'Marking all selected gifts as received. Continue?')
    def receive_gift(self, ids):
        try:
            query = db.session.query(Gift).filter(Gift.id.in_(ids))
            count = 0
            for gift in query.all():
                gift.received = True
                count += 1
            db.session.commit()
            flash(ngettext('Gift was marked as received.',
                           '%(count)s gifts were marked as received.',
                           count, count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(gettext('Failed to update received status on gifts. %(error)s', error=str(ex)), 'error')


class SponsorView(BaseView):
    form_columns = ['first_name', 'last_name', 'phone', 'email', 'children']
    column_formatters = {'children': util.sponsor_children_formatter}
    form_overrides = {
        'phone': PhoneNumberField,
    }
    form_rules = {
        rules.NestedRule([
            rules.NestedRule(
                [rules.Header('Sponsor Info'), 'first_name', 'last_name', 'phone', 'email']
            ),
            rules.NestedRule(
                [rules.HTML(f"""<small class="form-text text-muted">{SPONSOR_CHILD_DISCLAIMER}</small>"""),
                 'children']
            )
        ])
    }


class SponsorRequestView(BaseView):
    form_columns = ['first_name', 'last_name', 'phone', 'email', 'request_count', 'preferences']
    form_overrides = {
        'phone': PhoneNumberField,
    }
    column_labels = {'request_count': "Wishlists Requested"}
    form_rules = {
        rules.NestedRule([
            rules.NestedRule(
                [rules.Header('Sponsor Info'), 'first_name', 'last_name', 'phone', 'email', 'request_count',
                 'preferences']
            ),
            rules.HTML(f"""<small class="form-text text-muted">{SPONSOR_REQUEST_DISCLAIMER}</small>"""),
        ])
    }


class MiscView(BaseView):
    column_display_pk = True


