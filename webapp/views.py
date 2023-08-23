from flask_admin import expose, BaseView
from flask_admin.contrib.sqla import ModelView

from .models import db, Gift, Child


class IndexView(BaseView):

    @expose('/')
    def index(self):
        return self.render(
            'main/index.html',
        )


class RegisterView(BaseView):

    @expose('/', methods=['GET', 'POST'])
    def register(self):
        form = ChildView(Child, db.session).create_form()
        return self.render(
            'main/register.html',
            form=form,
            return_url='/'
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


class ChildView(BaseView):
    column_list = [
        'first_name', 'last_name', 'parent', 'dhs_case_worker', 'dhs_office', 'age', 'race', 'gender', 'fav_color',
        'shoe_size', 'clothing_size', 'gifts'
    ]
    form_columns = column_list
    inline_models = [(Gift, dict(form_columns=['id', 'gift']))]
    column_labels = {
        'dhs_case_worker': 'Case Worker',
        'dhs_office': 'DHS Office',
        'fav_color': 'Favorite Color',
        'parent': 'Foster Parent'
    }


class ParentView(BaseView):
    pass


class GiftView(BaseView):
    pass


class MiscView(BaseView):
    column_display_pk = True