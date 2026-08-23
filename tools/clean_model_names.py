import os
import shutil
from pathlib import Path

# Mapeamento de pastas antigas / desorganizadas para os nomes limpos e padronizados no disco
CLEAN_FOLDER_NAMES = {
    "bulldozer_caminho_excavador_aspirador_carro_gre_etc": "maquinas_pesadas",
    "cadeira": "cadeira",
    "caiu_luvas_culos_chapu_proteo_escada_carro_sem_etc": "queda_e_epis",
    "caixa_de_fundo_caixas_etiquetas": "etiquetas_e_caixas",
    "caixa_fechada_caixa_aberta_pacotes": "caixas_e_pacotes",
    "caixa_mquina_escaladeira_pessoa": "conteiner_e_canteiro",
    "caminho": "caminhao",
    "caminho_misturador_de_concreto_lixeira_caminho_etc": "caminhao_betoneira",
    "carro_carro_2": "carro",
    "chuveiro": "chuveiro_emergencia",
    "cono_de_segurana": "cone_seguranca",
    "culos_sem_culos": "oculos_protecao",
    "espao_vazio_espao_ocupado": "vagas_estacionamento",
    "etc_norm_norm": "submodelo_pressao_normal",
    "excavador_escavadeira_carro": "escavadeira",
    "extintor_extintor_2_extintor_3_excessive_pressure_etc": "submodelo_extintor_avarias",
    "garrafa_de_vidro_castanho_garrafa_de_vidro_limpo_etc": "frascos_e_garrafas",
    "ma_mala_mala_de_ramen_banana_garrafa_tigela_de_etc": "alimentos_e_utensilios",
    "medidor_manivela_tubo_fora_ala_de_segurana_etc": "submodelo_extintor_detalhes",
    "mochila_co2_bomba_mc_2a_bomba_mf_60_navio_yamato": "extintor_co2_silica",
    "nibus_grande_caminho_grande_nibus_longo_nibus_etc": "veiculos_pesados",
    "partes_do_extintor_medidor_bom_medidor_baixo_etc": "submodelo_extintor_componentes",
    "pessoa": "pessoa",
    "placa": "placa_sinalizacao",
    "produto_caixa": "item_caixa",
    "sinal_de_estacionamento": "sinal_estacionamento",
    "veste_sem_segurana_veste_de_segurana": "colete_seguranca",
    "extinguidor": "extintor_incendio",
    "fire_extinguisher_v6i": "submodelo_extintor_avarias",
    "fire_extinguisher_merged_v2i": "submodelo_extintor_componentes",
    "fire_extinguisher_new_dataset_v11i": "submodelo_extintor_detalhes",
    "press_v1i": "submodelo_pressao_normal"
}

def clean_and_rename():
    root = Path(__file__).resolve().parent.parent
    models_dir = root / "models"
    
    if not models_dir.exists():
        print(f"❌ Pasta de modelos não encontrada: {models_dir}")
        return

    print("🧹 Renomeando e organizando pastas dos modelos com nomes limpos e padronizados...")

    renamed_count = 0
    for old_name, new_name in CLEAN_FOLDER_NAMES.items():
        old_path = models_dir / old_name
        new_path = models_dir / new_name

        if old_path.exists():
            if old_path != new_path:
                if new_path.exists():
                    print(f"  ⚠️ A pasta de destino '{new_name}' já existe. Mesclando conteúdo de '{old_name}'...")
                    for item in old_path.iterdir():
                        dest_item = new_path / item.name
                        if not dest_item.exists():
                            shutil.move(str(item), str(dest_item))
                    shutil.rmtree(str(old_path))
                else:
                    shutil.move(str(old_path), str(new_path))
                print(f"  ✅ Renomeado: '{old_name}' -> '{new_name}'")
                renamed_count += 1
            else:
                print(f"  ℹ️ Pasta já possui o nome limpo: '{new_name}'")

    print(f"\n🎉 Concluído! {renamed_count} pastas organizadas com nomes limpos.")

if __name__ == "__main__":
    clean_and_rename()
