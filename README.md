# czii-umbrella-django
django project for data integration.  This should become the go-to place for people unfamiliar with where people store information on their workflow.

## developer installation

1. Making miniconda environment
```
conda create -n umbrella-django python=3.11
conda activate umbrella-django
```
2. Clone git repository and initialize submodules
```
git clone https://github.com/czimaginginstitute/czii-umbrella-django.git _your_clone_dir_
cd _your_clone_dir_
git submodule update --init --recursive

```
3. install requirements (I use pip even in conda env)
```
(cd _your_clone_dir_ if you didn't in the last step)
pip install -r ./requirements.txt
```
4. create settings.py for yourself in the project directory

   Django organizes its apps under a project directory that is duplicated in this repository.  The global settines are saved in a directory named also by the django project name.
```
cd umbrella
cp umbrella/settings.py.template umbrella/settings.py
```
5. migrate django database

   This repository includes database migration history.
```
python manage.py migrate
```
6. create supreuser per instruction in [django tutorial 2](https://docs.djangoproject.com/en/5.0/intro/tutorial02/) for your admin login.
```
python manage.py createsuperuser
```
7. run the following initialization scripts that creates a project, a grid, and a live processing plan.
```
python manage.py runscript 001_init
python manage.py runscript 002_permission (optional)
python manage.py runscript 003_init_multigrid
python manage.py runscript 004_init_processes
python manage.py runscript 005_init_pytom_pick
```
8. run django server locally at the default 8000 port
```
python manage.py runserver
```
9. view the main page at http://127.0.0.1/umbrella/

## Basic Code Structure

1. Base: This folder

1.1. umbrella: Django project 

Django documentation is [here](https://docs.djangoproject.com/en/5.2/)

1.1.1. umbrella: project-wide app  (url:BASE/)

   1.1.x the rest of folders are Django apps that map in url as a sub-directory in the same name (i.e. url:BASE/app_name)
   
   1.1.x.1 models.py: Where the database schema and behavior is defined. [Django model layer]([https://docs.djangoproject.com/en/5.2/topics/db/models/](https://docs.djangoproject.com/en/5.2/#the-model-layer)
```
            * Each models.Model sub-class maps to a database table in a name like app_name_modelname
            * Each attribute maps to a field
```
   1.1.x.2 urls.py: Where url pattern requests and the function links the backend view function to is under url:BASE/app_name
   
   1.1.x.3 views.py: Where the backend operation to present a view to the request is defined. returned context can be passed to django templates for display at the url that sent the request. [view layer](https://docs.djangoproject.com/en/5.2/#the-view-layer)
   
   1.1.x.4 apps.py: app configuration
   
   1.1.x.5 admin.py: Where visibility in [autometed-generated admin UI](https://docs.djangoproject.com/en/5.2/#the-admin) (url: BASE/admin) is defined 

   1.1.x.6 templates/app_name: directory containing template html files that urls.py is pointed to. [templates](https://docs.djangoproject.com/en/5.2/#the-template-layer)
   
   [django template language](https://docs.djangoproject.com/en/5.2/ref/templates/language/) is used to define variable from the query results and perform logic.
   
   1.1.x.7 migrations/: directory contains instruction of database migrations for each version of model change.
   
1.2. frontend: Next.js project
