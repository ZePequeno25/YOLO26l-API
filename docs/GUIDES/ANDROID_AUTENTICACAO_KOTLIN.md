# Guia de Autenticação Segura — Android Kotlin + API

Este guia cobre todas as técnicas de segurança implementadas no backend e como integrá-las no app Android com Kotlin.

## 0. Comportamento Atual do Backend (Importante)

Para o app funcionar sem erros de autenticação e sem bloqueio indevido, considere estas regras:

- O backend aceita token em múltiplos formatos:
    - Header `Authorization: Bearer <token>`
    - Form-data: `id_token`, `access_token` ou `token`
    - JSON: `id_token`, `access_token` ou `token`
- O backend normaliza tokens com ruído (ex.: `Bearer Bearer "token"`).
- Rotas internas/sistema podem retornar `404` sem autenticação admin (blindagem).
- Cada usuário pode executar **1 análise por vez**. Uma segunda análise simultânea retorna `429`.
- Existe rate limit global e por autenticação, então o cliente precisa tratar `429` com `Retry-After`.

---

## 1. Dependências (build.gradle.kts)

```kotlin
// Firebase BOM — gerencia versões automaticamente
implementation(platform("com.google.firebase:firebase-bom:33.0.0"))
implementation("com.google.firebase:firebase-auth-ktx")
implementation("com.google.firebase:firebase-appcheck-playintegrity")
implementation("com.google.firebase:firebase-appcheck-debug")   // apenas debug

// Rede
implementation("com.squareup.retrofit2:retrofit:2.11.0")
implementation("com.squareup.retrofit2:converter-gson:2.11.0")
implementation("com.squareup.okhttp3:okhttp:4.12.0")
implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

// DataStore (armazenar token com segurança)
implementation("androidx.datastore:datastore-preferences:1.1.1")
```

---

## 2. Fluxo Passwordless com Email Link

### 2.1 Enviar link de login

```kotlin
import com.google.firebase.auth.ActionCodeSettings
import com.google.firebase.auth.ktx.auth
import com.google.firebase.ktx.Firebase
import com.google.firebase.ktx.actionCodeSettings

fun sendSignInLink(email: String, onSuccess: () -> Unit, onError: (Exception) -> Unit) {
    val actionCodeSettings = actionCodeSettings {
        url = "https://SEU_DOMINIO.page.link/login"      // URL configurada no Firebase Console
        handleCodeInApp = true
        setAndroidPackageName(
            "com.seu.pacote",   // Package name do app
            true,               // Instala via Play Store se não existir
            "21"                // Min SDK version
        )
    }

    Firebase.auth.sendSignInLinkToEmail(email, actionCodeSettings)
        .addOnSuccessListener {
            // Salvar e-mail localmente para usar na validação do link
            saveEmailLocally(email)
            onSuccess()
        }
        .addOnFailureListener { onError(it) }
}
```

### 2.2 Processar o Deep Link recebido

No `Activity` que recebe o link (configurada no AndroidManifest como `intent-filter`):

```kotlin
import com.google.firebase.auth.ktx.auth
import com.google.firebase.ktx.Firebase

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    handleSignInLink(intent)
}

override fun onNewIntent(intent: Intent) {
    super.onNewIntent(intent)
    handleSignInLink(intent)
}

private fun handleSignInLink(intent: Intent) {
    val link = intent.data?.toString() ?: return
    if (!Firebase.auth.isSignInWithEmailLink(link)) return

    val email = getSavedEmail() ?: run {
        // E-mail não encontrado — pedir para o usuário digitar novamente
        showEmailPrompt { enteredEmail -> completeSignIn(enteredEmail, link) }
        return
    }
    completeSignIn(email, link)
}

private fun completeSignIn(email: String, link: String) {
    Firebase.auth.signInWithEmailLink(email, link)
        .addOnSuccessListener { result ->
            result.user?.getIdToken(true)?.addOnSuccessListener { tokenResult ->
                val firebaseIdToken = tokenResult.token ?: return@addOnSuccessListener
                // Trocar o Firebase ID Token pelo token da própria API
                exchangeForApiToken(firebaseIdToken)
            }
        }
        .addOnFailureListener { /* tratar erro */ }
}
```

---

## 3. Trocar Firebase Token pelo Token da API (Sem 401 falso)

Após obter o `idToken` do Firebase, chame `/auth/token`.

### 3.1 Models e Service com fallback

```kotlin
data class ApiTokenResponse(
    val success: Boolean,
    val access_token: String,
    val token_type: String,
    val expires_in: Int,
    val uid: String,
    val email: String?,
    val name: String?
)

data class ApiTokenJsonRequest(
    val id_token: String
)

interface AuthService {
    @POST("auth/token")
    suspend fun issueApiTokenJson(
        @Body body: ApiTokenJsonRequest,
        @Header("X-Firebase-AppCheck") appCheckToken: String? = null
    ): ApiTokenResponse

    @FormUrlEncoded
    @POST("auth/token")
    suspend fun issueApiTokenForm(
        @Field("id_token") idToken: String,
        @Header("X-Firebase-AppCheck") appCheckToken: String? = null
    ): ApiTokenResponse
}
```

### 3.2 Implementação recomendada

```kotlin
suspend fun exchangeForApiToken(firebaseIdToken: String): ApiTokenResponse {
    val appCheckToken = getAppCheckToken()

    val response = try {
        // Primeira tentativa: JSON
        authService.issueApiTokenJson(ApiTokenJsonRequest(firebaseIdToken), appCheckToken)
    } catch (e: HttpException) {
        // Fallback para cenários de form antigo
        if (e.code() == 415 || e.code() == 422 || e.code() == 400) {
            authService.issueApiTokenForm(firebaseIdToken, appCheckToken)
        } else {
            throw e
        }
    }

    tokenStore.saveToken(response.access_token, response.expires_in)
    return response
}
```

### 3.3 Regras para evitar erro no cliente

- Sempre salve `access_token` retornado pela API, não o token bruto do Firebase, para usar na análise.
- Nunca monte manualmente um valor tipo `Bearer Bearer ...`.
- Faça `trim()` antes de salvar e antes de enviar token.

---

## 4. Login com Google (fluxo alternativo)

```kotlin
// Interface Retrofit para /auth/google
data class GoogleAuthRequest(
    val id_token: String,
    val email: String,
    val displayName: String
)

data class GoogleAuthResponse(
    val success: Boolean,
    val access_token: String,
    val token_type: String,
    val expires_in: Int,
    val uid: String,
    val email: String,
    val name: String,
    val is_new_user: Boolean
)

interface AuthService {
    @POST("auth/google")
    suspend fun authenticateGoogle(
        @Body request: GoogleAuthRequest,
        @Header("X-Firebase-AppCheck") appCheckToken: String? = null
    ): GoogleAuthResponse
}
```

```kotlin
// Uso após obter credenciais Google Sign-In
suspend fun loginWithGoogle(idToken: String, email: String, displayName: String) {
    val appCheckToken = getAppCheckToken()
    val response = authService.authenticateGoogle(
        GoogleAuthRequest(idToken, email, displayName),
        appCheckToken
    )
    tokenStore.saveToken(response.access_token, response.expires_in)
}
```

---

## 5. Firebase App Check (Play Integrity)

### 5.1 Inicializar no Application

```kotlin
import com.google.firebase.Firebase
import com.google.firebase.appcheck.appCheck
import com.google.firebase.appcheck.playintegrity.PlayIntegrityAppCheckProviderFactory
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory
import com.google.firebase.initialize

class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Firebase.initialize(context = this)

        Firebase.appCheck.installAppCheckProviderFactory(
            if (BuildConfig.DEBUG)
                DebugAppCheckProviderFactory.getInstance()   // debug: token fixo
            else
                PlayIntegrityAppCheckProviderFactory.getInstance()  // produção
        )
    }
}
```

### 5.2 Obter token do App Check

```kotlin
import com.google.firebase.Firebase
import com.google.firebase.appcheck.appCheck
import kotlinx.coroutines.tasks.await

suspend fun getAppCheckToken(): String? {
    return try {
        Firebase.appCheck.getToken(false).await().token
    } catch (e: Exception) {
        null   // enviar null — o backend ignora quando ENABLE_APP_CHECK=False
    }
}
```

> **No backend:** defina `ENABLE_APP_CHECK=True` no `.env` para exigir o token em produção.

---

## 6. OkHttp Interceptor + Authenticator (Sem perda de sessão)

Use **Interceptor** para anexar token e **Authenticator** para refresh automático em `401`.

```kotlin
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

private fun normalizeToken(raw: String?): String? {
    if (raw.isNullOrBlank()) return null
    var value = raw.trim().trim('"').trim('\'')
    while (value.startsWith("Bearer ", ignoreCase = true)) {
        value = value.substring(7).trim().trim('"').trim('\'')
    }
    return value.ifBlank { null }
}

class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = runBlocking { normalizeToken(tokenStore.getToken()) }
        val request = if (token != null) {
            chain.request().newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }
        return chain.proceed(request)
    }
}

class TokenAuthenticator(
    private val tokenStore: TokenStore,
    private val authRepository: AuthRepository
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        // Evita loop infinito de retry
        if (responseCount(response) >= 2) return null

        val newToken = runBlocking {
            authRepository.refreshAccessTokenOrNull()
        } ?: return null

        return response.request.newBuilder()
            .header("Authorization", "Bearer ${normalizeToken(newToken)}")
            .build()
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}
```

### 6.1 Registrar no OkHttpClient

```kotlin
val okHttpClient = OkHttpClient.Builder()
    .addInterceptor(AuthInterceptor(tokenStore))
    .authenticator(TokenAuthenticator(tokenStore, authRepository))
    .addInterceptor(HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
        else HttpLoggingInterceptor.Level.NONE
    })
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(120, TimeUnit.SECONDS)
    .writeTimeout(120, TimeUnit.SECONDS)
    .retryOnConnectionFailure(true)
    .build()

val retrofit = Retrofit.Builder()
    .baseUrl("https://192.168.76.103:8000/")
    .client(okHttpClient)
    .addConverterFactory(GsonConverterFactory.create())
    .build()
```

> Em desenvolvimento sem HTTPS, use `http://` apenas na rede local e nunca em produção.

### 6.2 Chamada de análise sem perda de autenticação

Mesmo com `Authorization` automático pelo Interceptor, mantenha compatibilidade de fallback:

```kotlin
interface DetectionService {
    @Multipart
    @POST("detection/analyze")
    suspend fun analyze(
        @Part file: MultipartBody.Part,
        @Part("model") model: RequestBody,
        // Fallback opcional se algum ambiente remover headers
        @Part("access_token") accessToken: RequestBody? = null
    ): AnalysisResponse
}

suspend fun analyzeImage(filePart: MultipartBody.Part, modelBody: RequestBody) : AnalysisResponse {
    val token = normalizeToken(tokenStore.getToken())
    val fallback = token?.toRequestBody("text/plain".toMediaType())

    return withNetworkBackoff {
        detectionService.analyze(
            file = filePart,
            model = modelBody,
            accessToken = fallback
        )
    }
}
```

---

## 7. Tratamento de Bloqueios e Retry (429, 403, 404, rede)

O backend pode retornar:

- `429`: rate limit, análise concorrente ou proteção anti-rajada
- `403`: bloqueio temporário por comportamento suspeito
- `404`: rota interna oculta por segurança
- `401`: token expirado/inválido (precisa refresh)

### 7.1 Handler de rate limit (429)

```kotlin
import retrofit2.HttpException

suspend fun handleRateLimit(error: HttpException) {
    val retryAfter = error.response()
        ?.headers()
        ?.get("Retry-After")
        ?.toLongOrNull() ?: 60L

    // Mostrar contador regressivo para o usuário
    showRateLimitDialog(retryAfterSeconds = retryAfter)
}

// OU: usando Retry automático com delay
suspend fun <T> withRetryOnRateLimit(block: suspend () -> T): T {
    repeat(3) { attempt ->
        try {
            return block()
        } catch (e: HttpException) {
            if (e.code() != 429 || attempt == 2) throw e
            val retryAfter = e.response()?.headers()?.get("Retry-After")
                ?.toLongOrNull() ?: 60L
            delay(retryAfter * 1000)
        }
    }
    throw IllegalStateException("Unreachable")
}
```

### 7.2 Backoff para falhas de rede (SocketException/EOF)

```kotlin
import java.io.EOFException
import java.net.SocketException
import kotlin.math.pow

suspend fun <T> withNetworkBackoff(block: suspend () -> T): T {
    repeat(3) { attempt ->
        try {
            return block()
        } catch (e: Exception) {
            val retryable = e is SocketException || e is EOFException
            if (!retryable || attempt == 2) throw e

            val waitMs = (1000.0 * 2.0.pow(attempt.toDouble())).toLong() // 1s, 2s, 4s
            delay(waitMs)
        }
    }
    throw IllegalStateException("Unreachable")
}
```

### 7.3 Regra para rotas de sistema

Não chame rotas `/system`, `/errors`, `/docs`, `/detection/metrics` no app de usuário final.
Sem token admin, o backend retorna `404` por blindagem e isso é esperado.

### 7.4 Regra de concorrência da análise

Cada usuário só pode ter 1 análise em andamento.

- Se receber `429` na análise, exiba: "Já existe uma análise em andamento. Aguarde finalizar."
- Desabilite botão de enviar enquanto a requisição de análise estiver ativa.

---

## 8. Armazenar Token com Segurança (DataStore Preferences)

**Nunca** use `SharedPreferences` sem criptografia para tokens JWT.

```kotlin
import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import java.time.Instant

private val Context.dataStore by preferencesDataStore(name = "auth_prefs")

class TokenStore(private val context: Context) {
    private val KEY_TOKEN = stringPreferencesKey("access_token")
    private val KEY_EXPIRY = longPreferencesKey("token_expiry_epoch")

    suspend fun saveToken(token: String, expiresInSeconds: Int) {
        val expiryEpoch = Instant.now().epochSecond + expiresInSeconds
        context.dataStore.edit { prefs ->
            prefs[KEY_TOKEN] = token
            prefs[KEY_EXPIRY] = expiryEpoch
        }
    }

    suspend fun getToken(): String? {
        val prefs = context.dataStore.data.first()
        val token = prefs[KEY_TOKEN] ?: return null
        val expiry = prefs[KEY_EXPIRY] ?: 0L
        // Renovar com margem de 5 minutos antes de expirar
        return if (Instant.now().epochSecond < expiry - 300) token else null
    }

    suspend fun clearToken() {
        context.dataStore.edit { it.clear() }
    }
}
```

---

## 9. HTTPS / Certificate Pinning (Produção)

Em produção com domínio próprio, adicione o pin do certificado:

```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add("api.seudominio.com", "sha256/HASH_DO_SEU_CERTIFICADO==")
    .build()

val okHttpClient = OkHttpClient.Builder()
    .certificatePinner(certificatePinner)
    // ... resto da configuração
    .build()
```

> Para obter o hash: `openssl s_client -connect api.seudominio.com:443 | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64`

---

## 10. AndroidManifest — Deep Links para Email Link

```xml
<activity android:name=".LoginActivity">
    <!-- Deep Link para processar o link do Firebase -->
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data
            android:scheme="https"
            android:host="SEU_DOMINIO.page.link" />
    </intent-filter>
</activity>
```

---

## 11. Checklist de Segurança

| Item | Status | Como verificar |
|------|--------|----------------|
| Email Link habilitado no Firebase Console | ⬜ | Authentication > Sign-in method |
| SHA-1 e SHA-256 vinculados ao projeto Firebase | ⬜ | Project Settings > Your apps |
| App Links / Asset Links configurados | ⬜ | `/.well-known/assetlinks.json` no servidor |
| App Check + Play Integrity ativo em produção | ⬜ | `ENABLE_APP_CHECK=True` no `.env` da API |
| HTTPS obrigatório em produção | ⬜ | Certificado TLS 1.2+ no servidor |
| Token salvo em DataStore (não SharedPreferences) | ⬜ | Revisar `TokenStore` |
| Certificate Pinning ativo em produção | ⬜ | `CertificatePinner` no OkHttpClient |
| Rate limit tratado na UI (Retry-After) | ⬜ | Handler de HTTP 429 |
| 403 tratado na UI (bloqueio por 404s) | ⬜ | Handler HTTP 403 com `retry_after` |
| 404 de rotas internas tratado como segurança (não erro de app) | ⬜ | Evitar chamadas a `/system` e afins |
| Botão de análise bloqueado durante upload | ⬜ | Evitar 2 análises simultâneas por usuário |
| Fallback de token em JSON/form e normalização no cliente | ⬜ | Aceitar `id_token` e limpar `Bearer` duplicado |
| Logging desabilitado em release | ⬜ | `HttpLoggingInterceptor.Level.NONE` em release |
