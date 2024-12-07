# setup.py

from setuptools import setup, find_packages

setup(
   name="bitmex_trading_bot",
   version="1.0.0",
   packages=find_packages(),
   install_requires=[
       'ccxt>=2.0.0',
       'pandas>=1.3.0',
       'numpy>=1.20.0',
       'dash>=2.0.0',
       'dash-bootstrap-components>=1.0.0',
       'plotly>=5.3.0',
       'python-telegram-bot>=20.0',
       'python-dotenv>=0.19.0',
       'talib-binary>=0.4.24',
       'requests>=2.26.0',
