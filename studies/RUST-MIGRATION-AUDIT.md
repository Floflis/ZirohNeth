# Oxidação das dependências da ZeroNet (Rust it)

**Status:** estudo de migração, não implementação  
**Repositório analisado:** `FloflisPull/ZirohNeth`  
**Base analisada:** `main` em `dfb0e9ed390006cde9365354572120c62fcf6119`

## 1. Objetivo

Mapear dependências Python e componentes próprios que podem ser substituídos por Rust, priorizando segurança, desempenho, manutenção e builds reproduzíveis.

“Rust it” não significa reescrever o cliente inteiro de uma vez. A recomendação é uma migração incremental, mantendo Python como camada de aplicação/plugins/UI até que cada fronteira esteja estável.

Classificações usadas:

- **Alta:** bom candidato a módulo Rust isolado.
- **Média:** viável, mas depende de compatibilidade ou adaptação.
- **Baixa:** manter por enquanto; custo de reescrita supera benefício imediato.
- **Arquitetural:** exige redesenho maior, não substituição drop-in.

## 2. Mapa de dependências e componentes

| Componente Python / código | Uso confirmado | Candidato Rust | Prioridade | Observação |
|---|---|---|---|---|
| `gevent`, `greenlet` | loops, greenlets, sockets, timers, workers | Tokio | Arquitetural | Não é drop-in. Migrar por serviço/fronteira. |
| `msgpack` | protocolo de mensagens e streams | `rmp-serde`, `rmpv` | Alta | Preservar exatamente framing, tipos binários e compatibilidade antiga. |
| `hashlib` SHA-512/SHA-256 | hashes de arquivos e checksums | `sha2` | Alta | Manter SHA-512 truncado a 256 bits onde o protocolo exige. |
| `base58` | validação/decodificação de endereço Bitcoin | `bs58` | Alta | Cobrir checksum Base58Check e formatos aceitos. |
| `sslcrypto` | ECC/secp256k1, assinatura, recuperação, AES | `secp256k1`, `k256`, `aes`/`aes-gcm` conforme formato | Alta | Compatibilidade de assinatura/ECIES é requisito, não presumir equivalência. |
| `coincurve` / libsecp256k1 | aceleração e verificação secp256k1 | crate `secp256k1` ou FFI libsecp256k1 | Alta | Validar formato recoverable e serialização. |
| `rsa` | assinatura/verificação RSA | `rsa` (RustCrypto) | Média | Preservar PKCS#1 v1.5 + SHA-256 e DER/PEM aceitos. |
| `Crypt.ed25519.py` próprio | Ed25519 | `ed25519-dalek` | **Crítica** | O próprio arquivo alerta que operações com segredos não são side-channel safe. Substituir antes de usar para segredos. |
| `bencode_open` próprio | parser Bencode | `serde_bencode` ou `bendy` | Alta | Testar entradas malformadas, ordenação de chaves e bytes. |
| `subtl` próprio | BitTorrent UDP tracker (BEP 15) | implementação Rust própria pequena ou crate validado | Média | Protocolo simples, mas precisa manter wire format. |
| `aiobtdht`, `aioudp`, `asyncio_gevent` | DHT BitTorrent e integração com gevent | Tokio + implementação DHT compatível | Arquitetural | Não substituir sem plano de interoperabilidade DHT. |
| `requests`, `urllib` | HTTP(S), trackers e bootstrap | `reqwest` | Média | Proxy, Tor, TLS, redirects e headers precisam de testes. |
| `socks`, `sockshandler`, `SocksProxy.py` | SOCKS5 e monkey patch de sockets | `tokio-socks` / integração com `reqwest` | Média | Não perder a política de roteamento local/Tor/proxy. |
| `sqlite3` | banco de dados local | `rusqlite` ou `sqlx` | Média | Migrar só após definir fronteira de acesso e esquema. |
| `GitPython` | revisão/branch para debug | `gix` (gitoxide) | Baixa | Uso atual é pequeno; CLI Git pode continuar suficiente. |
| `websocket-client` | cliente WebSocket para API local | `tokio-tungstenite` | Média | UI e protocolo JSON devem permanecer compatíveis. |
| `gevent.pywsgi` + `gevent_ws` | servidor HTTP/WebSocket UI | `axum`/`hyper` + `tokio-tungstenite` | Arquitetural | Maior superfície de compatibilidade com wrappers. |
| `rich` | saída de terminal | manter Python ou CLI Rust | Baixa | Não justifica migração isolada. |
| `IPython` | console de depuração opcional | manter opcional | Baixa | Ferramenta de desenvolvimento, não caminho crítico. |
| `array`, `struct`, `difflib`, `json`, `re`, `pathlib` | estruturas/stdlib | std Rust | Baixa/Média | Migrar junto dos módulos que as usam, não por si só. |

A tabela registra usos vistos nos arquivos inspecionados. Não é uma SBOM completa e não afirma que todas as dependências transitivas foram auditadas.

## 3. Componentes próprios que merecem oxidação

### 3.1 Criptografia

Arquivos:

- `src/Crypt/ed25519.py`
- `src/Crypt/CryptBitcoin.py`
- `src/Crypt/CryptRsa.py`
- `src/Crypt/CryptHash.py`
- `src/lib/sslcrypto/`

Prioridade máxima para remover operações secretas da implementação Python Ed25519. O comentário do arquivo declara explicitamente que a implementação não é segura para chaves/dados secretos devido a timing e padrões de acesso à memória.

Proposta:

- Ed25519: `ed25519-dalek`.
- secp256k1: crate `secp256k1` ou `k256`, avaliando recuperação de chave e formatos legados.
- RSA: `rsa` RustCrypto, se a compatibilidade exigida estiver coberta.
- hashes: `sha2`.
- Base58: `bs58`.

Antes de substituir, construir vetores dourados com entradas/saídas do cliente atual para operações válidas. Não usar implementação Python insegura para criar novas chaves ou assinaturas durante a migração.

### 3.2 MessagePack e streams

`src/util/Msgpack.py` não é apenas um wrapper trivial. Ele:

- configura tratamento especial de bytes;
- preserva nomes de campos binários;
- trata compatibilidade antiga;
- escreve mapa MessagePack e injeta bytes de arquivo no stream.

Um módulo Rust pode implementar codec e framing, mas precisa passar testes byte a byte contra a implementação Python. `rmp-serde` pode ser apropriado para estruturas tipadas; `rmpv` pode ajudar quando for necessário preservar valores dinâmicos.

### 3.3 Bencode e tracker UDP

`src/lib/bencode_open/__init__.py` contém parser Bencode próprio. `src/lib/subtl/subtl.py` implementa tracker UDP segundo BEP 15.

São alvos bons para crates pequenos ou módulos Rust dedicados, desde que mantenham o formato exato e rejeitem entradas truncadas/malformadas de forma segura.

### 3.4 Concorrência e transporte

`gevent` aparece no núcleo de conexões, site announcer, workers, UI e armazenamento. Tokio é uma alternativa arquitetural, não uma biblioteca compatível com a API de gevent.

Estratégia recomendada:

1. não trocar gevent globalmente;
2. criar um serviço Rust isolado para uma responsabilidade;
3. estabelecer IPC explícito e versionado;
4. medir latência, memória, throughput e complexidade operacional;
5. migrar consumidores um a um;
6. só então avaliar uma runtime Tokio dominante.

Iroh pode ser o primeiro serviço Rust porque já é um transporte independente e não exige reescrever o TCP ZeroNet.

## 4. Arquitetura de integração Python ↔ Rust

Duas opções:

### Opção A: daemon/serviço Rust local

Python comunica com um processo Rust por IPC (Unix socket/named pipe ou protocolo local autenticado).

Vantagens:
- isolamento de falhas e memória;
- não acopla ABI Python ao runtime Rust;
- facilita executar testes e ferramentas Rust independentes;
- bom encaixe para Iroh, DHT ou serviço de blobs.

Desvantagens:
- ciclo de vida do processo;
- protocolo IPC e serialização adicionais;
- empacotamento multiplataforma.

### Opção B: extensão nativa com PyO3 + maturin

Vantagens:
- chamada direta de funções;
- boa opção para hash, codec e criptografia;
- menos overhead de IPC.

Desvantagens:
- ABI, wheels e builds por plataforma;
- cuidado com GIL e tarefas longas;
- maior acoplamento entre o core Python e a extensão.

**Recomendação:** daemon para subsistemas assíncronos/complexos (Iroh, DHT); PyO3 para funções determinísticas e isoladas (hash, codec, criptografia), depois de estabelecer vetores de compatibilidade.

## 5. Sequência recomendada

### Etapa 0: inventário e testes de referência

- [ ] Extrair dependências declaradas e dependências transitivas.
- [ ] Mapear imports reais e caminhos opcionais.
- [ ] Criar vetores de teste dourados para MessagePack, hashes, assinaturas, Base58, RSA e Bencode.
- [ ] Medir baseline de CPU, RAM, throughput e tempo de inicialização.
- [ ] Registrar plataformas e arquiteturas suportadas.

### Etapa 1: segurança e primitivas

- [ ] Substituir operações secretas Ed25519 por implementação Rust mantida.
- [ ] Criar módulo Rust para hashes e Base58.
- [ ] Criar testes de compatibilidade secp256k1/assinaturas recuperáveis.
- [ ] Auditar ECIES/AES antes de trocar a implementação.
- [ ] Definir política de zeroização de segredos e tratamento de erros.

### Etapa 2: codecs e protocolos pequenos

- [ ] Bencode parser/encoder.
- [ ] BitTorrent UDP tracker.
- [ ] MessagePack e framing de streams.
- [ ] Testes de fuzzing e limites de tamanho.

### Etapa 3: subsistemas de rede

- [ ] PoC Iroh isolada.
- [ ] Serviço DHT compatível com protocolo atual, se necessário.
- [ ] Cliente HTTP/SOCKS com política de proxy preservada.
- [ ] Medir interoperabilidade e fallback.

### Etapa 4: persistência e UI

- [ ] Avaliar `rusqlite`/`sqlx` apenas após estabilizar fronteiras.
- [ ] Avaliar WebSocket/HTTP Rust sem quebrar wrappers.
- [ ] Manter plugins Python funcionando durante a transição.

## 6. Regras de compatibilidade

- Não alterar formato de assinatura, hash ou endereço sem migração formal.
- Não trocar SHA-512 truncado por BLAKE3 em arquivos legados.
- Não substituir MessagePack por JSON/CBOR sem negociação explícita de versão.
- Não assumir que `tokio` substitui `gevent` sem reescrever o modelo de concorrência.
- Toda mudança deve ter teste cruzado Python ↔ Rust.
- Manter caminho Python de fallback enquanto a implementação Rust estiver em validação.
- Nenhuma chave privada deve atravessar logs, argumentos de processo ou IPC sem proteção.

## 7. Critérios de sucesso

- Resultados criptográficos compatíveis com vetores existentes.
- Testes de fuzzing sem panic explorável ou consumo ilimitado.
- Builds reproduzíveis para as plataformas suportadas.
- Redução mensurável de CPU/RAM ou melhoria de segurança/manutenção.
- Nenhuma regressão de interoperabilidade com peers antigos.
- Rollback simples por feature flag.

## 8. Referências

- Tokio: https://tokio.rs/
- PyO3: https://pyo3.rs/
- Maturin: https://www.maturin.rs/
- `rmp-serde`: https://docs.rs/rmp-serde/
- `rmpv`: https://docs.rs/rmpv/
- `sha2`: https://docs.rs/sha2/
- `bs58`: https://docs.rs/bs58/
- `ed25519-dalek`: https://docs.rs/ed25519-dalek/
- `secp256k1`: https://docs.rs/secp256k1/
- `k256`: https://docs.rs/k256/
- `rsa`: https://docs.rs/rsa/
- `bendy`: https://docs.rs/bendy/
- `serde_bencode`: https://docs.rs/serde_bencode/
- `reqwest`: https://docs.rs/reqwest/
- `tokio-socks`: https://docs.rs/tokio-socks/
- `rusqlite`: https://docs.rs/rusqlite/
- `gix`: https://docs.rs/gix/
- ZeroNet files: `src/Connection/`, `src/Peer/`, `src/Crypt/`, `src/util/`, `src/DHT/`, `src/lib/`, `plugins/`

## 9. TODO

- [ ] Fechar inventário completo a partir do arquivo de dependências e imports condicionais.
- [ ] Confirmar licenças e manutenção de cada crate antes de adoção.
- [ ] Fixar versões após PoCs e testes de compatibilidade.
- [ ] Definir matriz CI para Linux, Windows, macOS e Android/Termux conforme suporte desejado.
- [ ] Medir custo de distribuição de binários Rust.
- [ ] Abrir issues separadas por etapa; este estudo não autoriza reescrita imediata.
