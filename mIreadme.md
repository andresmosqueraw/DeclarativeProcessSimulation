Estos son los comandos que use pero igual me aparece otra vez error de permisos, es algo de mi pc:

git clone --recurse-submodules https://github.com/AdaptiveBProcess/DeclarativeProcessSimulation.git
cd DeclarativeProcessSimulation
git submodule update --init --recursive
cd GenerativeLSTM 
git checkout Declarative-Process
cd ..
cd GenerativeLSTM
conda env create -f environment.yml
conda activate deep_generator
cd ..
mkdir -p data/0.logs/PurchasingExample
mkdir -p data/1.predicton_models
mkdir -p data/2.hallucination_logs
mkdir -p data/2.input_logs
mkdir -p data/3.bps_asis
mkdir -p data/3.bps_tobe
mkdir -p data/4.simulation_results
docker pull nokal/simod
docker build -t java8-xvfb docs/example/java_docker_image
docker image ls

cp docs/example/PurchasingExample.csv data/0.logs/PurchasingExample/PurchasingExample.csv
cp docs/example/rules.ini data/0.logs/PurchasingExample/rules.ini


MODIFY dg_training.py
-------------------------------------------------------------------------------------------------------
FILENAME = 'PurchasingExample.csv'
--------------------------------------------------------------------------------------------------------

mkdir -p GenerativeLSTM/output_files

python dg_training.py
o para mi pc:
/home/andrew/miniconda3/envs/deep_generator/bin/python dg_training.py (esto solo para mi computadora porque pyenv esta interferiendo con conda y toca usar la ruta completa del entorno de conda)

sudo chown -R andrew:andrew data/
cp docs/example/configuration.yaml data/2.input_logs/PurchasingExample/configuration_original.yaml
# gzip -k docs/example/PurchasingExample.csv
# cp docs/example/PurchasingExample.csv.gz data/2.input_logs/PurchasingExample/
cp docs/example/configuration.yaml data/2.hallucination_logs/PurchasingExample/configuration_generated.yaml
# cp docs/example/PurchasingExample.csv.gz data/2.hallucination_logs/PurchasingExample/
/home/andrew/miniconda3/envs/deep_generator/bin/python dg_prediction.py


para probar todo otra vez

rm -rf data/0.logs/PurchasingExample/embedded_matix/
rm -rf data/1.predicton_models/PurchasingExample/

/home/andrew/miniconda3/envs/deep_generator/bin/python dg_training.py

rm -rf data/3.bps_asis/PurchasingExample/
rm -rf data/3.bps_tobe/PurchasingExample/
rm -rf data/4.simulation_results/PurchasingExample/
/home/andrew/miniconda3/envs/deep_generator/bin/python dg_prediction.py


compare stats:
/home/andrew/miniconda3/envs/deep_generator/bin/python compare_stats.py
/home/andrew/miniconda3/envs/deep_generator/bin/python visualize_stats.py


shortterm
cd DeclarativeProcessSimulation/shorterm
python run_complete_integration.py