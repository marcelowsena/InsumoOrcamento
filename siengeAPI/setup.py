from setuptools import setup, find_packages

setup(
    name="siengeapi",
    version="1.0.0",
    author="Seu Nome",
    author_email="seu.email@exemplo.com",
    description="Biblioteca para consultas e manipulação de dados do Sienge",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.6"
)