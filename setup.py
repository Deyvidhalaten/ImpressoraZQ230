from cx_Freeze import setup, Executable
import sys, os

includefiles = [
  ('templates','templates'),
  ('static','static')
]

setup(
  name="ImpressoraApp",
  version="1.0",
  description="App de Impressão",
  options={'build_exe':{
      'packages':['flask','jinja2'],
      'include_files':includefiles
  }},
  executables=[Executable('app.py', base=None)]
)
