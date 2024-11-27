conda create -n tracet_note python=3.10
conda activate tracet_note
pip install -r webapp_tracet/requirements_web.txt
cd webapp_tracet/tracet_package/
pip install .
cd -
conda install -n tracet_note ipykernel --update-deps --force-reinstall
pip install python-dotenv==1.0.1
pip install xmltodict
