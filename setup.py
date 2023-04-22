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
        "Django >=4, <5",
        "gunicorn >=20.1.0, <21",
        "django-mathfilters >=1.0.0, <2",
        "redis >= 4.5.1, <5",
        "sentry-sdk >= 1.12, <2",
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
