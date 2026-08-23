# Script PowerShell para renomear e organizar pastas dos modelos com nomes limpos
$modelsDir = "c:\Users\aborr\Projeto TCC\YOLO26l-API\models"

$map = @{
    "bulldozer_caminho_excavador_aspirador_carro_gre_etc" = "maquinas_pesadas"
    "cadeira" = "cadeira"
    "caiu_luvas_culos_chapu_proteo_escada_carro_sem_etc" = "queda_e_epis"
    "caixa_de_fundo_caixas_etiquetas" = "etiquetas_e_caixas"
    "caixa_fechada_caixa_aberta_pacotes" = "caixas_e_pacotes"
    "caixa_mquina_escaladeira_pessoa" = "conteiner_e_canteiro"
    "caminho" = "caminhao"
    "caminho_misturador_de_concreto_lixeira_caminho_etc" = "caminhao_betoneira"
    "carro_carro_2" = "carro"
    "chuveiro" = "chuveiro_emergencia"
    "cono_de_segurana" = "cone_seguranca"
    "culos_sem_culos" = "oculos_protecao"
    "espao_vazio_espao_ocupado" = "vagas_estacionamento"
    "etc_norm_norm" = "submodelo_pressao_normal"
    "excavador_escavadeira_carro" = "escavadeira"
    "extintor_extintor_2_extintor_3_excessive_pressure_etc" = "submodelo_extintor_avarias"
    "garrafa_de_vidro_castanho_garrafa_de_vidro_limpo_etc" = "frascos_e_garrafas"
    "ma_mala_mala_de_ramen_banana_garrafa_tigela_de_etc" = "alimentos_e_utensilios"
    "medidor_manivela_tubo_fora_ala_de_segurana_etc" = "submodelo_extintor_detalhes"
    "mochila_co2_bomba_mc_2a_bomba_mf_60_navio_yamato" = "extintor_co2_silica"
    "nibus_grande_caminho_grande_nibus_longo_nibus_etc" = "veiculos_pesados"
    "partes_do_extintor_medidor_bom_medidor_baixo_etc" = "submodelo_extintor_componentes"
    "pessoa" = "pessoa"
    "placa" = "placa_sinalizacao"
    "produto_caixa" = "item_caixa"
    "sinal_de_estacionamento" = "sinal_estacionamento"
    "veste_sem_segurana_veste_de_segurana" = "colete_seguranca"
}

foreach ($oldName in $map.Keys) {
    $newName = $map[$oldName]
    $oldPath = Join-Path $modelsDir $oldName
    $newPath = Join-Path $modelsDir $newName

    if (Test-Path $oldPath) {
        if ($oldPath -ne $newPath) {
            if (Test-Path $newPath) {
                Write-Host "⚠️ Mesclando $oldName em $newName..."
                Get-ChildItem -Path $oldPath | ForEach-Object {
                    $target = Join-Path $newPath $_.Name
                    if (-not (Test-Path $target)) {
                        Move-Item $_.FullName $target -Force
                    }
                }
                Remove-Item $oldPath -Recurse -Force
            } else {
                Move-Item $oldPath $newPath -Force
            }
            Write-Host "✅ Renomeado: $oldName -> $newName"
        }
    }
}
Write-Host "🎉 Organização de nomes limpos concluída!"
