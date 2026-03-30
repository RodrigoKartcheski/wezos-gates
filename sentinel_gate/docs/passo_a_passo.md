1 fazer o git clone

git clone https://github.com/RodrigoKartcheski/wezos-gates.git
cd wezos-gates
cd sentinel_gate




2 criar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

3 instalar as dependências
pip install -r requirements.txt

4 executar o sentinel_gate
python -m sentinel_gate.main --config samples/data_quality_contract_v1.json

5 Gerar Executável (.exe)
(duração estimada de 40 minutos)
No PowerShell, dentro da pasta sentinel_gate:
./build_exe.ps1

O executável será gerado na pasta dist/.
Para rodar como Studio: ./sentinel_gate.exe --studio

