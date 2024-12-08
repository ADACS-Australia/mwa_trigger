conda create -n tracet_note python=3.10
conda activate tracet_note
pip install -r webapp_tracet/requirements_web.txt
cd webapp_tracet/tracet_package/
pip install .
cd -
conda install -n tracet_note ipykernel --update-deps --force-reinstall
pip install python-dotenv==1.0.1
pip install xmltodict


# docs part
export PROJECT_PASSWORDS='{"C002":"password1","C3204":"password2","C3374":"password3","C3542":"password4","G0055":"password5","G0094":"password6"}'

pip install Sphinx==8.1.3
pip install numpydoc==1.8.0
pip install sphinx-automodapi==0.18.0
pip install sphinxcontrib-mermaid==1.0.0
pip install sphinx-rtd-theme==3.0.1