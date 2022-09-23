import setuptools

setuptools.setup(
    name="boogie-stats",
    version="0.0.1",
    description="A pass-through proxy for groovestats.com that records non-ranked song scores.",
    author="Rafał Florczak",
    author_email="florczak.raf+boogiestats@gmail.com",
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests >=2.26.0, <3",
        "Django >=4, <5",
        "gunicorn >=20.1.0, <21",
        "django-mathfilters >=1.0.0, <2",
    ],
    extras_require={
        "dev": [
            "pytest >=6.2.5, <7",
            "pytest-django >=4.4.0, <5",
            "black >=22.3.0, <22.4",
            "requests-mock >=1.9.3, <2",
            "flake8 >=4.0.1, <5",
            "djlint >= 1.1.1, <2",
            "bandit >= 1.7.4, <2",
        ],
    },
)
