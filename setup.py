from setuptools import setup, find_packages

setup(
    name='foster-christmas',
    version='1.0.0',
    author='Josh Price',
    author_email='joshkprice717@gmail.com',
    description='Hope for the Holidays Webapp',
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask_admin',
        'flask_sqlalchemy',
    ],
)

# run 'python setup.py install'