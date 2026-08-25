# 📱 Guia de Implementação Android (Projeto KelvinTech)

Este documento contém a instrução detalhada e os códigos-fonte em Kotlin para que o agente/desenvolvedor responsável pelo app Android `KelvinTech` exiba os **laudos do Ollama**, o **status de conformidade** e o **detalhamento dos 5 componentes do extintor** (Trava, Mangueira, Adesivo, Carga de Gás, Sinalização).

---

## 1. Atualização dos Data Classes Retrofit/Gson (`DetectionResponse.kt`)

No pacote do modelo de dados da API (ex: `com.kelvintech.data.model` ou `data/dto`):

```kotlin
package com.kelvintech.data.model

import com.google.gson.annotations.SerializedName

data class DetectionResponse(
    @SerializedName("requested_model") val requestedModel: String? = null,
    @SerializedName("compliance_status") val complianceStatus: String? = "CONFORME", // "CONFORME" ou "NÃO CONFORME"
    @SerializedName("compliance_alerts") val complianceAlerts: List<String>? = emptyList(),
    @SerializedName("compliance_report") val complianceReport: String? = null, // Laudo em frase única do Ollama
    @SerializedName("class_counts") val classCounts: Map<String, Int>? = emptyMap(),
    @SerializedName("sub_layer_analysis") val subLayerAnalysis: List<SubLayerAnalysisItem>? = emptyList()
)

data class SubLayerAnalysisItem(
    @SerializedName("object_class") val objectClass: String? = null,
    @SerializedName("category") val category: String? = null,
    @SerializedName("is_conforming") val isConforming: Boolean = true,
    @SerializedName("passed_items") val passedItems: List<String>? = emptyList(),
    @SerializedName("failed_items") val failedItems: List<String>? = emptyList(),
    @SerializedName("alerts") val alerts: List<String>? = emptyList()
)
```

---

## 2. Exibição na Interface do Usuário (`ResultActivity.kt` / `DetectionResultFragment.kt`)

Substitua ou adicione a lógica de manipulação da tela de resultado após receber a resposta `DetectionResponse` da API:

```kotlin
fun renderDetectionResult(response: DetectionResponse) {
    val isConforming = response.complianceStatus == "CONFORME"

    // 1. Tarja e Ícone de Status Geral
    if (isConforming) {
        cardStatusHeader.setCardBackgroundColor(ContextCompat.getColor(this, R.color.green_success))
        tvStatusTitle.text = "CONFORME (APROVADO)"
        ivStatusIcon.setImageResource(R.drawable.ic_check_circle)
    } else {
        cardStatusHeader.setCardBackgroundColor(ContextCompat.getColor(this, R.color.red_alert))
        tvStatusTitle.text = "NÃO CONFORME (ALERTA DE SEGURANÇA)"
        ivStatusIcon.setImageResource(R.drawable.ic_warning)
    }

    // 2. Laudo Descritivo em Linguagem Natural (Gerado pelo Ollama)
    val reportText = response.complianceReport 
        ?: "Análise concluída com sucesso. Nenhuma anormalidade detectada."
    tvOllamaReport.text = reportText

    // 3. Detalhamento dos 5 Componentes do Extintor (Sobcamada)
    val subLayers = response.subLayerAnalysis
    if (!subLayers.isNullOrEmpty()) {
        layoutSubLayerContainer.visibility = View.VISIBLE
        
        val builder = StringBuilder()
        for (item in subLayers) {
            builder.append("🔍 Sub-Inspeção: ${item.objectClass}\n")
            
            // Componentes Conformes (Verde)
            item.passedItems?.forEach { passed ->
                builder.append("  ✓ $passed: OK\n")
            }
            
            // Componentes Faltantes/Irregulares (Vermelho)
            item.failedItems?.forEach { failed ->
                builder.append("  ❌ $failed: FALTANDO / IRREGULAR\n")
            }
            builder.append("\n")
        }
        tvSubLayerDetails.text = builder.toString()
    } else {
        layoutSubLayerContainer.visibility = View.GONE
    }
}
```

---

## 3. Layout XML Recomendado (`activity_result.xml`)

```xml
<!-- Card do Laudo da IA (Ollama) -->
<androidx.cardview.widget.CardView
    android:id="@+id/cardOllamaReport"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_margin="16dp"
    app:cardCornerRadius="12dp"
    app:cardElevation="4dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="16dp">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="📋 Laudo de Auditoria IA (Ollama)"
            android:textStyle="bold"
            android:textSize="16sp"
            android:textColor="@color/black" />

        <TextView
            android:id="@+id/tvOllamaReport"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:textSize="14sp"
            android:lineSpacingExtra="4dp"
            android:textColor="@color/gray_800" />
    </LinearLayout>
</androidx.cardview.widget.CardView>

<!-- Container de Detalhamento da Sobcamada (5 Componentes) -->
<LinearLayout
    android:id="@+id/layoutSubLayerContainer"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="🔬 Análise de Componentes (Sobcamada)"
        android:textStyle="bold"
        android:textSize="15sp" />

    <TextView
        android:id="@+id/tvSubLayerDetails"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="6dp"
        android:fontFamily="monospace"
        android:textSize="13sp" />
</LinearLayout>
```
