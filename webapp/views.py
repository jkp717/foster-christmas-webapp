from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from flask import flash, request, redirect
from markupsafe import Markup
from flask_admin import expose, BaseView, AdminIndexView
from flask_admin.actions import action
from flask_admin.babel import ngettext
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.contrib.sqla.view import ModelView
from flask_admin.model.template import TemplateLinkRowAction
from flask_admin.babel import gettext
from flask_admin.form import rules, FormOpts
from wtforms_alchemy import PhoneNumberField
from wtforms.widgets import TelInput

from webapp.models import db, Gift, Child, Parent, DhsOffice, Gender, Race, ShoeSize, ClothingSize, FavColor, \
    Church, Sponsor, SponsorRequest, ParentArchive, SponsorArchive, ChildArchive, GiftArchive, GiftFulfillment
import webapp.util as util
from webapp.config import GIFT_DELIVERY_DISCLAIMER, REGISTER_CHILD_DISCLAIMER, SPONSORSHIP_DISCLAIMER, \
    SPONSOR_CHILD_DISCLAIMER, SPONSOR_REQUEST_DISCLAIMER, CHILD_REGISTRY_HELPER_TEXT


class PhoneNumberField2(PhoneNumberField):
    widget = TelInput()

class IndexView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render(
            'main/index.html',
        )

    @expose('/about-us')
    def about_us(self):
        return self.render(
            'main/about-us.html',
        )

    @expose('/privacy-policy')
    def privacy_policy(self):
        return self.render(
            'main/privacy-policy.html',
        )

class RegisterView(BaseView):
    can_create = True  # Sets if 'add another' option is present
    _raised_integrity_error = False  # flag if unique constraint fails

    def handle_integrity_error(self, exc):
        self._raised_integrity_error = False
        if isinstance(exc, IntegrityError):
            self._raised_integrity_error = True
            flash(
                gettext("Error occurred while processing your request! Try again shortly."),
                "error",
            )
            return True
        return False

    def skip_integrity_error(self, exc):
        self._raised_integrity_error = False
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
                model_view.handle_view_exception = self.skip_integrity_error
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
                else:
                    flash(gettext('An error occurred while processing your request. Please try again!'), 'error')
        # validation_attrs = ["required", "disabled", "readonly", "maxlength", "minlength", "pattern",]
        # setattr(form.phone.widget, 'validation_attrs', validation_attrs)
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
            else:
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
                model_view.handle_view_exception = self.skip_integrity_error
                model = model_view.create_model(form)
                if self._raised_integrity_error:
                    # Match all columns in _sponsor_uc constraint
                    model = db.session.query(Sponsor).filter(
                        Sponsor.first_name == form.first_name.data.title(),
                        Sponsor.last_name == form.last_name.data.title(),
                        Sponsor.email == form.email.data.lower(),
                    ).first()
                    for child in form.children.data:
                        child.sponsor_id = model.id
                    db.session.commit()
                if model:
                    flash(gettext('Thank you for your sponsorship!'), 'success')
                    return redirect('/')
                else:
                    if request.method == 'GET' or form.errors:
                        model_view.on_form_prefill(form, id)
            else:
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
    page_size = 50
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
    list_template = 'admin/child-list.html'
    column_list = [
        'child_id', 'parent', 'first_name', 'last_name', 'dhs_office', 'age', 'dhs_case_worker', 'gender',
        'sponsor_name', 'gifts', 'church', 'note'
    ]
    column_export_list = [
        'child_id', 'parent', 'parent.phone', 'parent.email', 'first_name', 'last_name', 'dhs_office', 'age',
        'dhs_case_worker', 'gender', 'sponsor_name', 'gifts', 'church', 'interests', 'note'
    ]
    form_exclude_columns = [
        'id', 'is_split', 'child_id', 'church', 'note', 'sponsor_name', 'parent.phone', 'parent.email'
    ]
    column_editable_list = ['child_id', 'church', 'note']
    column_descriptions = {
        "church": "Church given child's gift registration (if applicable)",
        "sponsor_name": "Sponsor assigned to this child",
        "gifts": "Count of gifts registered (click link to see gifts)",
        "interests": "favorite character, interests, or hobbies"
    }
    column_default_sort =  'numeric_sort_child_id'
    column_sortable_list = [
        ('child_id', ('numeric_sort_child_id',)), ('parent', 'parent.last_name'), 'first_name', 'last_name',
        'dhs_case_worker', ('dhs_office', 'dhs_office.office'), 'age', ('race', 'race.race'), ('gender', 'gender.gender'),
        ('fav_color', 'fav_color.color'), ('shoe_size', 'shoe_size.size'), ('clothing_size', 'clothing_size.size'),
        ('church', 'church.church'), ('sponsor', 'sponsor.last_name')
    ]
    column_filters = util.get_child_filters(Child, Sponsor, Parent)
    column_searchable_list = (Gift.gift, 'interests')
    form_rules = [
        rules.NestedRule([rules.Header('Foster Parent'), 'parent', rules.Macro('render_child_list')]),
        rules.NestedRule([
            rules.Header('Add Foster Child'), 'first_name', 'last_name', 'dhs_case_worker',
            'dhs_office', 'age', 'race', 'gender', 'fav_color', 'shoe_size', 'clothing_size', 'interests'
        ]),
        rules.NestedRule([
            'gifts',
            *[rules.Macro('form_helper_text', msg=t) for t in CHILD_REGISTRY_HELPER_TEXT],
        ])
    ]
    inline_models = [(Gift, dict(form_columns=['id', 'gift']))]
    column_labels = {
        'dhs_case_worker': 'Case Worker',
        'dhs_office': 'DHS Office',
        'fav_color': 'Fav. Color',
        'parent': 'Foster Parent',
        'note': 'Notes',
        'has_sponsor': 'Sponsored',
        'sponsor_name': 'Sponsor'
    }
    column_formatters = {
        'gifts': util.gift_list_formatter,
        'child_id': util.child_id_formatter
    }
    column_formatters_export = {
        'gifts': util.gift_list_export_formatter
    }
    column_extra_row_actions = [
        TemplateLinkRowAction(
            template_name='custom_row_actions.split_gifts_action',
        )
    ]

    def get_query(self):
        query = super().get_query()
        return query.options(joinedload(self.model.gifts), joinedload(self.model.sponsor))

    @expose('/')
    def index_view(self):
        self._refresh_filters_cache()
        return super().index_view()

    @expose('/split', methods=['GET', 'POST'])
    def split_gifts(self):
        child_id = request.args.get('id')
        child_model_view = ChildView(Child, db.session)
        gift_model_view = BaseView(Gift, db.session)
        child = child_model_view.get_one(child_id)

        if request.method == 'POST':
            og_id = child.child_id
            selected_ids = request.form.getlist('rowid')

            left_gifts = db.session.query(Gift).filter(Gift.child_id == og_id, db.not_(Gift.id.in_(selected_ids))).all()
            split_gifts = db.session.query(Gift).filter(Gift.child_id == og_id, Gift.id.in_(selected_ids)).all()

            a_id = f"{og_id}A"
            b_id = f"{og_id}B"

            child.child_id = a_id
            child.is_split = True
            for gift in left_gifts:
                gift.child_id = a_id

            cpy = {k: v for k, v in child.__dict__.items() if k not in ('_sa_instance_state', 'id')}

            new_child = Child(**cpy)
            new_child.child_id = b_id
            new_child.is_split = True
            for gift in split_gifts:
                gift.child_id = b_id

            db.session.add(new_child)
            db.session.commit()
            return redirect(self.get_url('.index_view'))

        return self.render(
            'admin/split-gifts.html',
            data=child.gifts,
            count=len(child.gifts),
            list_columns=(('gift', 'Gift'),),
            get_pk_value=gift_model_view.get_pk_value,
            get_value=gift_model_view.get_list_value,
            return_url=self.get_url('.index_view'),
        )


class ChildArchiveView(ChildView):
    can_edit = False
    column_list = ChildView.column_list + ['year']
    column_export_list = ChildView.column_export_list + ['year']
    column_filters =  util.get_child_filters(ChildArchive, SponsorArchive, ParentArchive)
    column_searchable_list = [GiftArchive.gift]
    inline_models = [(GiftArchive, dict(form_columns=['id', 'gift']))]
    column_formatters = None
    column_formatters_export = None
    column_extra_row_actions = None
    # To remove the custom page, override the method and set it to None
    split_gifts = None


class ParentView(BaseView):
    form_columns = ['first_name', 'last_name', 'email', 'phone', 'gift_delivery']
    # noinspection PyTypeChecker
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
    column_filters = util.get_parent_filters(Parent)
    column_labels = {
        'gift_delivery': 'DHS Delivery'
    }
    form_overrides = {
        'phone': PhoneNumberField2,
    }


class ParentArchiveView(ParentView):
    can_edit = False
    column_filters = util.get_parent_filters(ParentArchive)


class GiftView(BaseView):
    # Setup relational model variables
    CHILD_MODEL = Child
    column_display_pk = True
    column_filters = util.get_gift_filters(Gift, CHILD_MODEL)
    column_searchable_list = ['gift']
    column_sortable_list = {
        ('child', 'child.last_name'), 'create_date', 'gift', 'received', ('child', 'child.sponsor_name'), 'id'
    }
    column_list = ['id', 'create_date', 'child', 'received', 'gift']
    column_export_list = [
        'child_id', 'child.last_name', 'child.first_name', 'child.age', 'child.gender', 'gift', 'child.sponsor_name',
        'received', 'create_date'
    ]
    column_details_list = column_list + ['child.sponsor_name',]
    column_labels = {
        'id': 'Gift Id',
        'child.last_name': 'Child Last',
        'child.first_name': 'Child First',
        'child.age': 'Age',
        'child.fav_color': 'Fav Color',
        'child.shoe_size': 'Shoe Size',
        'child.clothing_size': 'Clothing Size',
        'child.gender.gender': 'Gender',
        'child.sponsor_name': 'Sponsor',
        'create_date': 'Registered Date'
    }

    def get_query(self):
        query = super().get_query()
        return query.options(
            joinedload(self.model.child).joinedload(self.CHILD_MODEL.gender),
            joinedload(self.model.child).joinedload(self.CHILD_MODEL.sponsor),
            joinedload(self.model.child).joinedload(self.CHILD_MODEL.fav_color)
        ).distinct()

    @action('receive_gift', 'Mark as Received', 'Marking all selected gifts as received. Continue?')
    def receive_gift(self, ids):
        try:
            query = db.session.query(self.model).filter(self.model.id.in_(ids))
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


class GiftArchiveView(GiftView):
    can_edit = False
    CHILD_MODEL = ChildArchive
    column_filters = util.get_gift_filters(GiftArchive, CHILD_MODEL)
    receive_gift = None


class SponsorView(BaseView):
    form_columns = ['first_name', 'last_name', 'phone', 'email', 'children']
    column_formatters = {'children': util.sponsor_children_formatter}
    form_overrides = {
        'phone': PhoneNumberField2,
    }
    # noinspection PyTypeChecker
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
    # noinspection PyTypeChecker
    form_rules = {
        rules.NestedRule([
            rules.NestedRule(
                [rules.Header('Sponsor Info'), 'first_name', 'last_name', 'phone', 'email', 'request_count',
                 'preferences']
            ),
            rules.HTML(f"""<small class="form-text text-muted">{SPONSOR_REQUEST_DISCLAIMER}</small>"""),
        ])
    }


class GiftFulfillmentView(BaseView):
    can_edit = True
    can_create = False
    can_delete = False
    column_display_actions = False
    # extra_js = ['/static/js/list-refresh.js']
    list_template = 'admin/list-refresh.html'
    column_list = [
        'child_id', 'child.last_name', 'child.first_name', 'is_received', 'received_date', 'is_pickup', 'pickup_date'
    ]
    column_editable_list = ['is_pickup', 'is_received']
    column_labels = {
        "is_pickup": "Picked Up",
        "is_received": "Gifts Received",
        "child.first_name": "First Name",
        "child.last_name": "Last Name"
    }
    column_sortable_list = [
        ('child_id', ('child.numeric_sort_child_id',)), 'child.first_name', 'child.last_name', 'is_received',
        'received_date', 'is_pickup', 'pickup_date'
    ]
    column_filters = util.get_gift_fulfillment_filters(GiftFulfillment, Child)
    column_formatters = {
        'received_date': util.datetime_formatter,
        'pickup_date': util.datetime_formatter,
    }


class MiscView(BaseView):
    column_display_pk = True
