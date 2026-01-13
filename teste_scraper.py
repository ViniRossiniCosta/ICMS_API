# test_scraper.py
from icms_scraper import ICMS_Scraper

print("Iniciando teste do scraper...")

# Cria o scraper
scraper = ICMS_Scraper()  # False para VER o navegador

try:
    # Testa extração
    dados = scraper.scrape()
    if dados:
        print("\n✅ SUCESSO! Dados extraídos:")
        print(f"   - Total de estados: {len(dados)}")
        print(f"   - Exemplo SP→RJ: {dados.get('SP', {}).get('RJ', 'N/A')}")
        print(f"   - Exemplo MG→BA: {dados.get('MG', {}).get('BA', 'N/A')}")
        
        # Testa salvar JSON
        scraper.salvar_json("teste_output.json")
        print("\n✅ JSON salvo em: teste_output.json")
    else:
        print("\n❌ ERRO: Nenhum dado extraído")
        
finally:
    scraper.fechar()