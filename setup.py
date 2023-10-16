from setuptools import setup, find_packages

setup(
    name='foster-christmas',
    version='1.1.0',
    author='Josh Price',
    author_email='joshkprice717@gmail.com',
    description='Hope for the Holidays Webapp',
    packages=find_packages(),
    install_requires=[
        'email-validator==2.0.0.post2',
        'Flask==3.0.0',
        'Flask-Admin==1.6.1',
        'Flask-SQLAlchemy==3.1.1',
        'MarkupSafe==2.1.3',
        'phonenumbers==8.13.22',
        'SQLAlchemy==2.0.22',
        'SQLAlchemy-Utils==0.41.1',
        'typing_extensions==4.8.0',
        'WTForms==3.0.0',
        'WTForms-Alchemy==0.18.0',
        'WTForms-Components==0.10.5'
    ],
)

# run 'python setup.py install'