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
cd _your_clone_dir_
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
