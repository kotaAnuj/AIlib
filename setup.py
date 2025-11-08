from setuptools import setup, find_packages

setup(
    name="ailib",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
    entry_points={
        'console_scripts': [
            'ailib=ailib_core:cli',
        ],
    },
    author="Your Name",
    description="Universal AI Programming Library",
    python_requires='>=3.8',
)


#pip install -e .
#ailib init myapp  # (instead of python ailib_core.py init)