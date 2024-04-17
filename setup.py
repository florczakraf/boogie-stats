import setuptools

setuptools.setup(
    name="boogie-stats",
    version="0.0.1",
    description="A pass-through proxy for groovestats.com that records non-ranked song scores.",
    author="Rafał Florczak",
    author_email="florczak.raf+boogiestats@gmail.com",
    license="AGPLv3",
    packages=setuptools.find_packages(where=".", include=["boogiestats*"]),
    include_package_data=True,
    install_requires=[
        "requests >=2.26.0, <3",
        "Django >=5, <6",
        "gunicorn >=22.0.0, <23",
        "django-mathfilters >=1.0.0, <2",
        "redis >=4.5.1, <5",
        "sentry-sdk >=1.12, <2",
        "django-bootstrap-icons == 0.8.7",
        "django-prometheus >=2.3.1, <3",
        "prometheus-client == 0.18.0",
        "django-ipware >=5.0.2, <6",
        "django-formset >=1.3.8, <2",
    ],
    extras_require={
        "dev": [
            "pytest ~= 7.3.0",
            "pytest-django ~= 4.5.2",
            "black ~= 23.3.0",
            "requests-mock ~= 1.10.0",
            "flake8 ~= 6.0.0",
            "djlint ~= 1.23.0",
            "bandit ~= 1.7.5",
        ],
    },
)
