from sqlalchemy.exc import IntegrityError

from flask import flash, request, redirect, Markup, current_app
from flask_admin import expose, BaseView, AdminIndexView
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.contrib.sqla import ModelView
from flask_admin.babel import gettext
from flask_admin.form import rules, FormOpts
from wtforms_alchemy import PhoneNumberField
from flask_admin.contrib.sqla.filters import FilterLike, FilterEqual

from .models import db, Gift, Child, Parent, DhsOffice, Gender, Race, ShoeSize, ClothingSize, FavColor
from .util import get_race_options, get_gender_options, get_fav_color_options, get_shoe_size_options, \
    get_dhs_office_options, get_clothing_size_options, title_case_formatter


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
                        Parent.first_name == form.first_name.data.upper(),
                        Parent.last_name == form.last_name.data.upper(),
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
            form.parent.data = parent
            form.parent.render_kw = {'disabled': ''}
            form_opts = FormOpts(
                widget_args=model_view.form_widget_args,
                form_rules=model_view._form_create_rules  # noqa
            )
            if model_view.validate_form(form):
                model = model_view.create_model(form)
                if model:
                    flash(gettext('Our records have been updated! Add another child or click finish.'), 'success')
                    if '_add_another' in request.form:
                        return redirect(self.get_url('register.child', parent_id=parent_id))
                    return redirect('/')
        flash(Markup(Markup(current_app.config['REGISTER_CHILD_DISCLAIMER'])))
        return self.render(
            'main/register.html',
            form=form,
            form_opts=form_opts,
            submit_text='Finish',
            return_url='/',
            add_another=True,
            parent=parent
        )

    def is_visible(self):
        return False


class BaseView(ModelView):
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
        'parent', 'first_name', 'last_name', 'dhs_case_worker', 'dhs_office', 'age', 'race', 'gender', 'fav_color',
        'shoe_size', 'clothing_size', 'gifts'
    ]
    column_filters = [
        'age',
        FilterLike(Parent.last_name, 'Parent Last Name'),
        FilterLike(Parent.first_name, 'Parent First Name'),
        FilterLike('dhs_case_worker', 'Case Worker'),
        FilterLike('first_name', 'Child First Name'),
        FilterLike('last_name', 'Child Last Name'),
        FilterEqual(DhsOffice.office, 'DHS Office', options=get_dhs_office_options),
        FilterEqual(Race.race, 'Child Race', options=get_race_options),
        FilterEqual(Gender.gender, 'Child Gender', options=get_gender_options),
        FilterEqual(ShoeSize.size, 'Shoe Size', options=get_shoe_size_options),
        FilterEqual(ClothingSize.size, 'Clothing Size', options=get_clothing_size_options),
        FilterEqual(FavColor.color, 'Favorite Color', options=get_fav_color_options)
    ]
    column_searchable_list = [Gift.gift]
    form_rules = [
        rules.NestedRule([rules.Header('Foster Parent'), 'parent', rules.Macro('render_child_list')]),
        rules.NestedRule([rules.Header('Add Foster Child'), *column_list[1:]])
    ]
    form_columns = column_list
    inline_models = [(Gift, dict(form_columns=['id', 'gift']))]
    column_labels = {
        'dhs_case_worker': 'Case Worker',
        'dhs_office': 'DHS Office',
        'fav_color': 'Favorite Color',
        'parent': 'Foster Parent'
    }

    @expose('/')
    def index_view(self):
        self._refresh_filters_cache()
        return super(ChildView, self).index_view()


class ParentView(BaseView):
    form_columns = ['first_name', 'last_name', 'phone', 'email']
    form_rules = {
        rules.FieldSet(rules=form_columns, header='Foster Parent')
    }
    form_overrides = {
        'phone': PhoneNumberField,
    }


class GiftView(BaseView):
    pass


class MiscView(BaseView):
    column_display_pk = True