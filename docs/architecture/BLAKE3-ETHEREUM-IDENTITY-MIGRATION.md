# 🌈 ZirohNeth — BLAKE3/BLAKE2b, identidade Ethereum e migração de sites Bitcoin

> **Status:** estudo técnico e proposta de arquitetura. Não é uma implementação concluída nem uma decisão final de algoritmo.
>
> **Data:** 17/11/2026
>
> **Escopo:** substituir ou paralelizar os hashes de conteúdo atuais, introduzir endereços Ethereum como identidade/autoridade de sites, assinar manifests com essas identidades e definir uma migração explícita dos sites Bitcoin legados.

---

# 🌈 1. Resumo executivo

A primeira etapa criptográfica da ZirohNeth pode ser dividida em três trilhas relacionadas, mas independentes:

1. **Integridade de conteúdo:** introduzir BLAKE3 ou BLAKE2b como algoritmo identificável no manifest, mantendo leitura dos hashes legados.
2. **Identidade e assinatura:** aceitar endereços Ethereum (`0x` + 40 dígitos hexadecimais) e validar assinaturas EIP-712, sem confundir isso com a assinatura Bitcoin atual.
3. **Migração:** publicar uma última versão assinada do site Bitcoin informando o endereço Ethereum sucessor, preservar o conteúdo antigo em modo histórico e estabelecer uma regra terminal de atualização no cliente ZirohNeth.

Recomendação de engenharia:

- Não substituir o campo antigo `sha512` por um hash de outro algoritmo sem identificar o algoritmo no manifest.
- Manter verificação dos sites Bitcoin existentes.
- Usar **EIP-712** para novas assinaturas de manifest, com um domínio ZirohNeth e campos explícitos de versão, site, sequência e digest.
- Começar com contas Ethereum EOA para validação offline; planejar ERC-1271 para smart wallets.
- Fazer a migração como um protocolo com prova cruzada: a chave Bitcoin antiga autoriza o novo endereço, e a chave Ethereum nova reconhece a identidade antiga e a versão final.
- Não prometer congelamento global apenas com um campo JSON: clientes novos precisam de um checkpoint verificável e uma regra de anti-rollback. Clientes ZeroNet antigos não conhecem essa regra.

**Ainda precisa ser decidido:** BLAKE3-256, BLAKE3-XOF-512, BLAKE2b-256 ou BLAKE2b-512 como hash primário. O estudo deixa a decisão aberta para benchmark e teste de interoperabilidade.

---

# 🌈 2. Auditoria do código atual

A análise abaixo foi feita sobre os arquivos disponíveis na branch `main` do repositório `FloflisPull/ZirohNeth`, em 17/11/2026.

## 🌈 2.1 Hash atual: não é um SHA-512 completo no manifest

Arquivo: `src/Crypt/CryptHash.py`

A função `sha512sum()`:

1. inicializa `hashlib.sha512()`;
2. lê o arquivo em blocos de 65.536 bytes;
3. calcula o SHA-512 completo;
4. retorna somente os primeiros 32 bytes, ou os primeiros 64 caracteres hexadecimais.

Portanto, o campo chamado `sha512` atualmente contém **SHA-512 truncado para 256 bits**. Ele não contém 512 bits e também não é o algoritmo padronizado SHA-512/256, que usa uma inicialização diferente.

A classe `Sha512t` repete a mesma semântica de truncamento.

## 🌈 2.2 Onde o hash de arquivo é usado

Arquivo: `src/Content/ContentManager.py`

Pontos confirmados:

- `hashFile()` calcula o hash dos arquivos e grava o resultado no campo `sha512`.
- `verifyFile()` recalcula `CryptHash.sha512sum()` e compara com `file_info["sha512"]`.
- A lógica de arquivos opcionais também usa esse identificador.
- `PeerHashfield` deriva um identificador de 16 bits dos primeiros quatro caracteres hexadecimais do hash.
- `getFileChanges()` usa o campo `sha512` para reconhecer arquivos removidos/renomeados.

Arquivo: `src/Peer/PeerHashfield.py`

O hashfield não guarda o hash completo. Ele reduz o hash aos primeiros 16 bits para compor o índice compacto de disponibilidade. Isso significa que a migração de algoritmo deve atualizar também os caches e garantir que a identificação de hashes de algoritmos diferentes não seja misturada.

## 🌈 2.3 `content.json` não é validado como um arquivo comum

O `content.json` raiz é um caso especial:

- `hashFiles()` ignora arquivos chamados `content.json`.
- `verifyFile()` valida `content.json` por assinatura e regras de conteúdo, em vez de comparar seu conteúdo com um SHA-512.
- O conteúdo da assinatura é serializado com `json.dumps(..., sort_keys=True)`.
- `signContent()` usa `CryptBitcoin.sign()`.
- `verifyFile()` usa `CryptBitcoin.verify()` para recuperar/verificar o endereço do assinante.

Logo, a mudança de hash de arquivos não troca automaticamente a assinatura do manifest. São duas operações distintas:

- **Hash do arquivo:** detecta alteração no conteúdo de cada arquivo.
- **Assinatura do manifest:** autentica a declaração de arquivos, hashes, permissões, timestamp e demais metadados.

O próprio `content.json` precisa ser serializado de forma determinística para ser assinado. Para interoperabilidade Python/Rust, `sort_keys=True` não deve ser tratado como uma especificação criptográfica universal.

## 🌈 2.4 Identidade Bitcoin está espalhada pela arquitetura

Arquivos observados:

- `src/Crypt/CryptBitcoin.py`
- `src/util/Electrum.py`
- `src/Site/Site.py`
- `src/Site/SiteManager.py`
- `src/Content/ContentManager.py`

Comportamento atual:

- `CryptBitcoin.py` usa secp256k1 e recuperação de assinatura para derivar endereços Bitcoin.
- `util/Electrum.py` implementa o formato de mensagem Bitcoin e o double-SHA256 usado na assinatura.
- `ContentManager.signContent()` converte a chave privada em endereço Bitcoin, confere se ele é um signatário permitido e assina o JSON.
- `verifyFile()` recupera e compara o endereço do assinante.
- O endereço raiz do site participa da lista de signatários válidos.

Há três incompatibilidades diretas com Ethereum:

1. `SiteManager.isAddress()` só aceita atualmente `^[A-Za-z0-9]{26,35}$`.
2. `Site.__init__()` remove todos os caracteres não alfanuméricos do endereço. Isso removeria o prefixo `0x`.
3. `CryptBitcoin` interpreta assinatura e chave no formato Bitcoin, não no padrão de mensagens/typed data Ethereum.

A migração precisa criar uma camada de identidade e assinatura com esquemas explícitos. Não se deve simplesmente passar um endereço Ethereum para as funções Bitcoin.

---

# 🌈 3. Hashes: BLAKE3 versus BLAKE2b

## 🌈 3.1 O que significam os tamanhos

| Algoritmo | Saída | Semântica |
|---|---:|---|
| SHA-512 atual no ZeroNet | 32 bytes | SHA-512 truncado para 256 bits |
| BLAKE3 padrão | 32 bytes | Saída padrão de 256 bits |
| BLAKE3 XOF-512 | 64 bytes | Saída estendida de 512 bits do XOF |
| BLAKE2b-256 | 32 bytes | BLAKE2b parametrizado para 32 bytes |
| BLAKE2b-512 | 64 bytes | BLAKE2b parametrizado para 64 bytes |

### BLAKE3-512 não é uma falsificação

BLAKE3 é uma função XOF (*Extendable Output Function*). Ela pode gerar uma saída de 64 bytes ou de outros comprimentos. Portanto, `BLAKE3-XOF-512` é uma saída real de 512 bits.

A ressalva é que **512 bits de saída não significam 512 bits de segurança**. A especificação BLAKE3 declara como alvo um nível de segurança de 128 bits. Além disso, a saída padrão de 32 bytes é o prefixo dos primeiros 32 bytes de uma saída estendida de 64 bytes. Pedir 64 bytes aumenta o tamanho armazenado, mas não eleva o nível de segurança declarado pelo desenho da função.

Para o protocolo, utilizar o nome inequívoco `blake3-xof-512`, em vez de sugerir que existe uma variante fixa BLAKE3-512 semelhante ao SHA-512.

### BLAKE2b-512 é diferente

BLAKE2b recebe o tamanho de digest como parâmetro do algoritmo. `BLAKE2b-256` e `BLAKE2b-512` são configurações de saída distintas; uma saída curta não é simplesmente o prefixo da saída maior.

Na biblioteca padrão do Python:

```python
import hashlib

digest_256 = hashlib.blake2b(data, digest_size=32).digest()
digest_512 = hashlib.blake2b(data, digest_size=64).digest()
```

A documentação do Python especifica que BLAKE2b aceita saídas de 1 a 64 bytes e que tamanhos diferentes produzem valores diferentes, não prefixos um do outro.

## 🌈 3.2 Qual escolher?

| Critério | BLAKE3-XOF-512 | BLAKE2b-512 |
|---|---|---|
| Saída de 64 bytes | Sim | Sim |
| Saída extensível | Sim | Não no mesmo modelo |
| Saída padrão | 32 bytes | 64 bytes |
| Paralelismo interno | Árvore paralelizável; SIMD e multithreading | Suporta modo árvore, mas o uso comum sequencial não paraleliza automaticamente um único arquivo |
| Bibliotecas Python | Pacote `blake3` | `hashlib` |
| Bibliotecas Rust | `blake3` | `blake2` |
| Multihash | Código BLAKE3 `0x1e`, com tamanho no campo de comprimento | Códigos específicos por tamanho |
| Consideração principal | Velocidade e paralelismo; 64 bytes não elevam sua segurança declarada | Saída de 512 bits convencional e tamanho configurável |

**Orientação provisória:**

- Se a prioridade é um digest de 64 bytes e interoperabilidade direta entre Python/Rust, fazer benchmark de BLAKE2b-512 e BLAKE3-XOF-512.
- Se a prioridade é manter o tamanho do campo atual, comparar BLAKE3-256 e BLAKE2b-256.
- Não declarar um algoritmo vencedor antes dos vetores cruzados, benchmark em arquivos grandes e teste com CID/Multihash.
- Para evitar confusão, gravar o algoritmo e o tamanho explicitamente. Nunca inferir algoritmo apenas pelo comprimento hexadecimal.

## 🌈 3.3 IPFS, Multihash e `--only-hash`

Multihash possui códigos para BLAKE2b:

- `blake2b-256`: código `0xb220`, permanente no registro.
- `blake2b-512`: código `0xb240`, marcado como draft no registro consultado.

BLAKE3 usa o código `0x1e`, marcado como draft no registro de multicodecs consultado. O formato Multihash guarda o código do algoritmo e o comprimento do digest.

O Kubo disponibiliza `--hash` em `ipfs add` e `--only-hash` para calcular sem gravar blocos no repositório local. A disponibilidade efetiva depende da lista de hashes permitidos na instalação.

Teste local recomendado:

```bash
# Consulte primeiro os hashes aceitos por esta instalação do Kubo.
ipfs cid hashes --supported | grep -Ei 'blake2|blake3'

# Calcule um CIDv1 sem armazenar/pinar o conteúdo.
ipfs add -Q --only-hash --cid-version=1 --hash=blake2b-512 ./arquivo.bin

# Teste BLAKE3 separadamente.
ipfs add -Q --only-hash --cid-version=1 --hash=blake3 ./arquivo.bin
```

**Atenção:** `ipfs add` retorna um CID de um objeto UnixFS/DAG. O arquivo pode ser dividido em blocos, e o resultado depende do chunker, do codec, de raw leaves e das opções de importação. O CID retornado não deve ser tratado como o hash direto dos bytes do arquivo que o `ContentManager` espera no campo de hash de arquivo.

`--only-hash` evita escrever os blocos no repositório local; não transforma o CID em digest simples do arquivo.

O Kubo documenta que arquivos maiores que o tamanho de chunk são divididos em blocos e que chunkers diferentes geram CIDs diferentes para o mesmo arquivo.

---

# 🌈 4. Estratégia de hash para os manifests

## 🌈 4.1 Compatibilidade por versão

Não reutilizar o campo `sha512` para guardar BLAKE3 ou BLAKE2b. Ele já tem uma semântica legada específica.

Durante a transição, um arquivo pode ter dois hashes:

```json
{
  "files": {
    "index.html": {
      "size": 1024,
      "sha512": "HASH_SHA512_TRUNCADO_LEGADO",
      "blake3-xof-512": "HASH_BLAKE3_XOF_512"
    }
  },
  "hash_policy": {
    "primary": "blake3-xof-512",
    "legacy": "sha512-truncated-256"
  },
  "content_format": 2
}
```

Este JSON é ilustrativo, não um esquema já implementado.

Regras sugeridas:

1. Cliente legado continua lendo `sha512` e ignora campos desconhecidos, desde que o formato real atual permita isso.
2. Cliente novo interpreta `content_format` e `hash_policy`.
3. Enquanto houver compatibilidade, verificar os dois hashes quando ambos estiverem presentes.
4. Uma vez encerrada a transição, novo conteúdo pode deixar de publicar o hash legado.
5. Um cliente que não conhece o algoritmo declarado deve falhar de forma explícita, não aceitar o arquivo sem verificação.
6. Não inferir algoritmo pelo número de caracteres.
7. Não misturar entradas de hashfield de algoritmos diferentes sem incluir o identificador do algoritmo na chave lógica.

## 🌈 4.2 Campos e nomes

Preferir nomes não ambíguos:

- `sha512-truncated-256` para documentar o legado com precisão.
- `blake3-xof-512` para 64 bytes obtidos do XOF.
- `blake3-256` para a saída padrão.
- `blake2b-256` e `blake2b-512` para parâmetros específicos de BLAKE2b.

O protocolo poderá usar um objeto `hash_policy` global, mas cada digest precisa permanecer identificável e verificável sem depender de convenções externas.

## 🌈 4.3 `content.json` e serialização canônica

O conteúdo do manifest precisa ser autenticado antes de confiar em `files`, `files_optional`, permissões, regras, endereços e metadados.

A serialização atual via `json.dumps(sort_keys=True)` não é uma especificação suficiente para implementações independentes em Python, Rust e outras linguagens.

Proposta:

- Adotar RFC 8785 (JSON Canonicalization Scheme, JCS) para produzir bytes determinísticos.
- Rejeitar propriedades JSON duplicadas.
- Restringir números aos limites de interoperabilidade do JCS; inteiros que não podem ser representados exatamente devem ser strings.
- Definir quais campos são removidos antes de calcular o digest: campos de assinatura e outros campos autorreferenciais.
- Criar vetores de teste idênticos em Python e Rust.

O digest canônico pode ser calculado com o algoritmo selecionado para o conteúdo e assinado como um campo tipado EIP-712. A assinatura não deve assinar uma representação JSON variável por whitespace ou ordem de propriedades.

---

# 🌈 5. Identidade Ethereum

## 🌈 5.1 Endereço EOA

Uma conta Ethereum EOA usa uma chave secp256k1. O endereço é formado pelos últimos 20 bytes do Keccak-256 da chave pública não comprimida, sem o byte inicial `0x04`, e apresentado com `0x` seguido de 40 caracteres hexadecimais.

Exemplo de formato:

```text
0x0123456789abcdef0123456789abcdef01234567
```

Não é um endereço Bitcoin codificado de outra maneira. O algoritmo de derivação e o formato de assinatura são diferentes.

## 🌈 5.2 EIP-55

EIP-55 define a representação em hexadecimal com letras maiúsculas/minúsculas como checksum visual.

Regras propostas:

- Validar tamanho de 20 bytes.
- Validar o checksum EIP-55 quando o endereço for apresentado em mixed-case.
- Normalizar para lowercase para comparação e chaves internas.
- Produzir EIP-55 para exibição e cópia.
- Preservar `0x` sempre.

O endereço exibido pode ser checksummed, enquanto o identificador interno usa a forma normalizada. Não remover pontuação do endereço.

## 🌈 5.3 Não misturar endereço de EOA e smart contract

Uma EOA tem chave privada correspondente e permite recuperação de assinatura ECDSA.

Uma conta de contrato não possui necessariamente uma chave privada diretamente correspondente. Smart wallets podem validar assinaturas por ERC-1271 (`isValidSignature(bytes32,bytes)`).

Para a primeira versão:

- **MVP:** EOA Ethereum com EIP-712 e recuperação de endereço.
- **Extensão:** ERC-1271 para smart wallets, multisig e contas contratuais.
- Registrar o tipo de validador em vez de presumir que todos os endereços `0x` funcionam via recuperação ECDSA.

ERC-1271 exige consultar o contrato em uma rede EVM. Portanto, sua validação não é puramente offline. O cliente precisa definir a chain usada, o RPC/fonte de estado e a política de bloco/estado em que a assinatura será validada.

## 🌈 5.4 Correções exigidas no código

### `src/Site/SiteManager.py`

O `isAddress()` atual aceita apenas Base58 de 26 a 35 caracteres. Introduzir validadores por tipo:

- `bitcoin-legacy`: formato Bitcoin antigo já suportado.
- `ethereum-eoa`: 20 bytes hexadecimais, prefixo `0x`, validação EIP-55 quando aplicável.
- `ethereum-contract`: endereço `0x` que requer validação ERC-1271, caso habilitado.

Não aceitar qualquer string de 40 hexadecimais sem decidir explicitamente o tipo.

### `src/Site/Site.py`

O construtor atual remove todos os caracteres não alfanuméricos do endereço. Isso apagaria o `0x`.

Trocar a sanitização genérica por parse/normalização específica de identidade. Preservar a forma canônica do endereço e os campos derivados usados por discovery, trackers e caches.

### `src/Crypt/CryptBitcoin.py`

Não sobrescrever as funções Bitcoin para passar a interpretar Ethereum. Separar os esquemas:

```text
CryptBitcoin
  - verify_legacy_message()
  - recover_legacy_address()

CryptEthereum
  - sign_eip712()
  - recover_eip712_address()
  - verify_eip712()
  - verify_erc1271()  # requer provider/RPC
```

Pode existir uma interface genérica `IdentityVerifier`, mas as implementações criptográficas e os formatos de assinatura precisam continuar isolados.

---

# 🌈 6. Assinatura Ethereum de sites

## 🌈 6.1 EIP-191 versus EIP-712

EIP-191 define mensagens Ethereum assináveis e o prefixo usado por `personal_sign`.

EIP-712 define a assinatura de dados estruturados, incluindo domínio, nome de protocolo, versão e campos tipados.

Para manifests de sites, **EIP-712 é a escolha recomendada**. O usuário deve ver que está assinando uma atualização do ZirohNeth, e não uma sequência opaca de bytes.

Não adotar assinatura de bytes arbitrários sem contexto para o formato definitivo do manifest.

## 🌈 6.2 Domínio e tipo de mensagem

Esboço ilustrativo de estrutura EIP-712:

```text
EIP712Domain:
  name: "ZirohNeth"
  version: "1"
  chainId: <decisão explícita do protocolo>

SiteUpdate:
  siteAddress: address
  contentDigest: bytes
  hashAlgorithm: string
  contentFormat: uint32
  sequence: uint64
  previousUpdateDigest: bytes32
  modified: uint64
```

Observações:

- O `contentDigest` representa os bytes canônicos do manifest, usando o algoritmo declarado.
- `siteAddress` deve corresponder à identidade Ethereum do site.
- `sequence` deve ser monotônico para aquele site.
- `previousUpdateDigest` encadeia versões e dificulta substituição silenciosa por uma versão antiga.
- `modified` é informativo e não substitui sequência monotônica.
- `chainId` precisa ser uma decisão consciente: incluir um chain ID no domínio vincula a assinatura àquele contexto de rede. O endereço EOA, por sua vez, pode ser o mesmo em várias redes.
- A cadeia de versões e a aplicação precisam impedir replay. EIP-712 oferece domínio e typed data, mas não implementa sozinho a política de replay do aplicativo.

A assinatura deve ser serializada com um formato versionado e independente do formato de assinatura Bitcoin.

## 🌈 6.3 Por que não usar somente `personal_sign`

`personal_sign` é útil para mensagens simples, mas não descreve tão bem uma atualização de conteúdo. Além disso, um formato próprio de assinatura sem domínio e sequência amplia o risco de uma assinatura ser reutilizada em outro contexto.

EIP-712 torna os campos tipados e fornece um domínio. Ainda assim, a ZirohNeth deve incluir identidade, versão, sequência e digest anterior para tratar replay e rollback.

## 🌈 6.4 Smart wallets e ERC-1271

A validação de EOA pode recuperar o endereço a partir da assinatura.

Para smart wallets, a aplicação deve chamar `isValidSignature` e exigir o magic value `0x1626ba7e`.

Isto cria dependências adicionais:

- chain ID escolhido para validação;
- provider/RPC;
- estado do contrato no bloco considerado;
- política de reorg e disponibilidade do provider;
- comportamento quando o contrato não existe ou não responde.

Não fazer fallback silencioso de ERC-1271 para ECDSA quando uma assinatura de contrato falhar.

---

# 🌈 7. Migração de um site Bitcoin existente

## 🌈 7.1 Objetivo de UX

O site Bitcoin antigo deverá exibir uma mensagem clara, derivada de um campo de migração assinado em seu último `content.json`:

> Este site migrou para uma identidade Ethereum. Esta versão é histórica e não receberá novas atualizações no protocolo ZirohNeth. Acesse o novo endereço: `0x...`.

O conteúdo antigo pode continuar legível e replicável. O novo site tem uma identidade distinta e não deve sobrescrever a identidade antiga na base de dados local.

## 🌈 7.2 Prova cruzada de migração

A migração deve vincular criptograficamente os dois endereços:

1. O dono assina a última versão do site antigo com a chave Bitcoin legada.
2. O `content.json` antigo inclui um objeto `migration` com endereço Ethereum de destino, endereço Bitcoin de origem, digest da versão final, versão do protocolo e indicação de encerramento.
3. O dono assina uma declaração com a nova conta Ethereum, reconhecendo o endereço Bitcoin antigo e o digest final.
4. O novo site Ethereum inclui a prova de origem, a assinatura Bitcoin final e a confirmação Ethereum.
5. O cliente ZirohNeth verifica ambas as provas antes de mostrar a migração como autenticada.

Exemplo conceitual:

```json
{
  "migration": {
    "status": "migrated",
    "from": {
      "scheme": "bitcoin-legacy",
      "address": "1LegacyBitcoinAddress..."
    },
    "to": {
      "scheme": "ethereum-eoa",
      "address": "0x0123456789abcdef0123456789abcdef01234567"
    },
    "finalContentDigest": "DIGEST_DA_VERSAO_FINAL",
    "finalSequence": 42,
    "protocol": "zirohneth-migration-v1",
    "updatePolicy": "terminal"
  }
}
```

O JSON acima é um exemplo de formato, não uma implementação nem um schema final.

## 🌈 7.3 Como congelar a versão Bitcoin

O cliente ZirohNeth deve tratar a migração autenticada como um **tombstone terminal** para o identificador Bitcoin:

- armazenar o checkpoint de migração;
- marcar o site antigo como histórico/read-only;
- continuar permitindo leitura e replicação histórica;
- recusar manifests posteriores do endereço Bitcoin antigo como atualizações;
- não aceitar que um manifest posterior remova o campo `migration` e reabra a identidade antiga;
- apresentar ao usuário o endereço Ethereum sucessor.

### Limitação importante

Um campo dentro de `content.json` não impede, sozinho, que um software antigo aceite uma nova assinatura Bitcoin. Clientes ZeroNet antigos não conhecem a regra de tombstone da ZirohNeth.

Também existe o problema de uma instalação nova receber apenas uma cópia antiga do manifest, sem saber que uma migração posterior já aconteceu. Para garantir estado terminal global, a ZirohNeth precisa de um checkpoint verificável que novos clientes consigam consultar:

- registro on-chain de migração; ou
- outro mecanismo distribuído e verificável de checkpoints, com política de confiança e anti-equivocação documentada.

Sem isso, o congelamento é garantido para clientes que já observaram e armazenaram o tombstone, mas não necessariamente para clientes novos que recebem uma versão desatualizada.

**Não destruir nem descartar a chave Bitcoin como mecanismo de congelamento.** Isso prejudica recuperação e não revoga cópias antigas da chave. O congelamento deve ser uma regra verificável do protocolo, não uma suposição operacional sobre a perda da chave.

## 🌈 7.4 O que preservar

- Arquivos históricos e respectivos hashes originais.
- Assinatura final Bitcoin e endereço de origem.
- Digest do último manifest Bitcoin.
- Endereço Ethereum de destino.
- Assinatura EIP-712 do novo dono.
- Relação verificável entre a versão final antiga e a versão inicial nova.
- Informação legível para o usuário, sem redirecionamento silencioso.

---

# 🌈 8. Bibliotecas recomendadas

## 🌈 8.1 Python

| Função | Biblioteca | Uso |
|---|---|---|
| Compatibilidade SHA-512 legado | `hashlib` | Verificar hashes antigos |
| BLAKE2b-256/512 | `hashlib.blake2b` | Hash parametrizado por `digest_size` |
| BLAKE3 | `blake3` | Hash normal e XOF com comprimento explícito |
| EOA Ethereum, EIP-191 e EIP-712 | `eth-account` | Assinar, codificar e recuperar typed data |
| Endereços e Keccak | `eth-utils` | `keccak`, checksum EIP-55 e utilidades Ethereum |
| Chamadas a contratos | `web3.py` | Consultar ERC-1271 em uma rede EVM |
| JSON canônico | `rfc8785` | RFC 8785 / JCS |

Sugestão de responsabilidades:

- `hashlib` para SHA-512 legado e BLAKE2b.
- `blake3` para BLAKE3-256 ou saída XOF de 64 bytes.
- `eth-account` como API principal de assinatura EIP-712 e recuperação.
- `eth-utils` para validação/checksum e operações Keccak.
- `web3.py` apenas quando a validação ERC-1271 exigir RPC.
- `rfc8785` para bytes JSON canônicos.

## 🌈 8.2 Rust

| Função | Crate | Uso |
|---|---|---|
| Compatibilidade SHA-512 legado | `sha2` | Verificar hashes antigos |
| BLAKE2b | `blake2` | Digest BLAKE2b com tamanho parametrizado |
| BLAKE3 | `blake3` | Hash padrão e XOF com `finalize_xof()` |
| Primitivos Ethereum | `alloy-primitives` | Tipos `Address`, bytes fixos e Keccak |
| Typed data EIP-712 | `alloy-sol-types` | Tipos Solidity e digest EIP-712 |
| Assinatura Ethereum | `alloy-signer` | Trait e APIs para assinatura |
| Assinante local | `alloy-signer-local` | Chave local EOA, suporte a K256/secp256k1 |
| Provider/RPC | `alloy-provider` | Consultas on-chain, inclusive ERC-1271 |
| JSON canônico | `serde_json_canonicalizer` | RFC 8785 / JCS |
| Compatibilidade ECC de baixo nível | `k256` | Alternativa caso seja necessário implementar validação diretamente |

Preferir Alloy como camada Ethereum de alto nível, em vez de criar parsing, Keccak, EIP-712 e recuperação de assinatura manualmente. Usar `k256` diretamente somente quando houver uma necessidade concreta de controle de baixo nível.

## 🌈 8.3 Divisão de responsabilidades Python/Rust

Uma arquitetura possível:

- Python mantém a integração com o ZeroNet legado, os arquivos de conteúdo e o fluxo atual de plugins.
- Rust oferece primitivas criptográficas determinísticas, hashing de alto desempenho e componentes compartilhados.
- Uma interface interna estável define entradas/saídas e versões de algoritmo.
- Vetores de teste comuns garantem que Python e Rust calculem exatamente o mesmo resultado.

Não é obrigatório reescrever o cliente inteiro para Rust antes de introduzir os novos esquemas.

---

# 🌈 9. Plano de implementação por etapas

## 🌈 Etapa 0 — Vetores e decisões de formato

- [ ] Escolher os identificadores definitivos dos algoritmos.
- [ ] Produzir vetores de teste para SHA-512 truncado, BLAKE3-256, BLAKE3-XOF-512, BLAKE2b-256 e BLAKE2b-512.
- [ ] Definir o schema versionado de `content.json`.
- [ ] Definir o canonicalizador JSON e os campos removidos antes da assinatura.
- [ ] Fixar o esquema EIP-712 e decidir a política de `chainId`.
- [ ] Documentar regras de sequência, digest anterior e replay.
- [ ] Não alterar ainda o formato legado de sites Bitcoin.

## 🌈 Etapa 1 — Hash paralelo

- [ ] Ler manifests antigos usando SHA-512 truncado.
- [ ] Criar suporte de leitura para os novos campos de hash.
- [ ] Publicar ambos os hashes durante a janela de compatibilidade.
- [ ] Atualizar hashfield/cache para não misturar algoritmos.
- [ ] Testar arquivos pequenos, arquivos maiores que o limite de chunk do IPFS e arquivos muito grandes.
- [ ] Medir desempenho em CPU móvel e desktop.
- [ ] Testar Python/Rust com o mesmo corpus de vetores.

## 🌈 Etapa 2 — Identidade Ethereum EOA

- [ ] Criar módulo separado `CryptEthereum`.
- [ ] Implementar parse e normalização do endereço `0x`.
- [ ] Implementar EIP-55 para validação visual.
- [ ] Alterar `SiteManager.isAddress()` para dispatch por esquema.
- [ ] Remover sanitização genérica de `Site.__init__()`.
- [ ] Criar serialização versionada de endereço e tipo de identidade.
- [ ] Implementar recuperação/verificação EIP-712.
- [ ] Validar assinatura e endereço em implementações Python e Rust.

## 🌈 Etapa 3 — Manifest assinado com EIP-712

- [ ] Definir tipos EIP-712 completos.
- [ ] Definir hash canônico do manifest.
- [ ] Implementar assinatura e recuperação EOA.
- [ ] Adicionar sequência monotônica e digest anterior.
- [ ] Criar vetores de interoperabilidade entre `eth-account` e Alloy.
- [ ] Rejeitar replay, sequência repetida, assinatura em domínio errado e digest divergente.

## 🌈 Etapa 4 — Migração Bitcoin → Ethereum

- [ ] Criar schema `migration-v1`.
- [ ] Assinar o manifest final com a chave Bitcoin original.
- [ ] Criar a declaração Ethereum de aceitação da identidade antiga.
- [ ] Verificar as duas assinaturas e o digest final.
- [ ] Criar tombstone terminal persistente para o identificador antigo.
- [ ] Exibir a mensagem de migração e o endereço novo.
- [ ] Manter o conteúdo antigo disponível em modo histórico.
- [ ] Decidir como novos clientes obtêm o checkpoint mais recente.
- [ ] Testar peers maliciosos que tentam servir versões antigas.

## 🌈 Etapa 5 — Smart wallets

- [ ] Adicionar validação ERC-1271.
- [ ] Definir chain ID e fonte de estado.
- [ ] Fixar política de bloco para validação.
- [ ] Testar carteiras multisig e smart wallets reais.
- [ ] Implementar cache com expiração e proteção contra falhas de RPC.
- [ ] Não bloquear sites EOA quando ERC-1271 estiver indisponível.

---

# 🌈 10. Matriz de testes obrigatórios

## 🌈 Hash

- [ ] Empty input, `abc`, arquivos binários e conteúdo UTF-8.
- [ ] Arquivos em tamanhos abaixo e acima de 2 MiB.
- [ ] Stream em blocos diferentes precisa produzir o mesmo resultado.
- [ ] BLAKE3-256 precisa coincidir com os primeiros 32 bytes de BLAKE3-XOF-512.
- [ ] BLAKE2b-256 não deve ser tratado como prefixo de BLAKE2b-512.
- [ ] Hashes antigos precisam continuar verificáveis.
- [ ] Hashfield deve distinguir ou isolar algoritmos.

## 🌈 Manifest e assinatura

- [ ] Python e Rust geram exatamente os mesmos bytes JCS.
- [ ] Uma mudança em qualquer campo protegido invalida a assinatura.
- [ ] Campos de assinatura não podem criar referência circular no digest.
- [ ] O endereço recuperado deve coincidir com `siteAddress`.
- [ ] Assinaturas EIP-712 de domínio ou versão errados devem falhar.
- [ ] Sequência duplicada e atualização antiga devem ser rejeitadas.
- [ ] Campos grandes e números acima da faixa segura do JCS devem ser tratados explicitamente.

## 🌈 Identidade e migração

- [ ] Endereço Bitcoin antigo continua sendo aceito pelo modo legado.
- [ ] Endereço Ethereum em lowercase e checksum EIP-55 é normalizado corretamente.
- [ ] Prefixo `0x` nunca é removido.
- [ ] A assinatura Bitcoin antiga continua verificável.
- [ ] A migração exige prova da chave antiga e da chave nova.
- [ ] Um terceiro não pode declarar arbitrariamente a migração de um site.
- [ ] Um manifest antigo não pode reabrir um site congelado depois de conhecido o tombstone.
- [ ] Uma instalação nova consegue descobrir o checkpoint mais recente conforme a política escolhida.
- [ ] Falha de RPC não deve transformar assinatura inválida em válida.

---

# 🌈 11. Riscos e decisões ainda abertas

| Questão | Risco | Próxima decisão |
|---|---|---|
| BLAKE3-XOF-512 ou BLAKE2b-512? | Tamanho e semântica de hash incompatíveis | Benchmark, vetores e teste Multihash |
| Manter 256 ou adotar 512 bytes de saída? | Mais tráfego sem necessariamente mais segurança | Definir requisito de digest, não escolher pelo número |
| EIP-712 chainId | Pode restringir assinatura a uma rede | Definir se identidade é cross-chain e qual domínio é usado |
| Smart wallets | Verificação exige estado on-chain | EOA-only no MVP ou ERC-1271 desde o início |
| Canonicalização JSON | Diferenças de serialização quebram assinaturas | RFC 8785 e corpus cruzado |
| Freeze de site Bitcoin | Clientes novos podem receber estado antigo | Checkpoint terminal verificável ou registro on-chain |
| Hashfield antigo | Cache/PEX pode misturar IDs | Versionar e invalidar/reconstruir caches |
| Endereços como chave de banco | IDs Bitcoin e Ethereum têm formatos distintos | Identidade tipada e normalização explícita |

---

# 🌈 12. Referências técnicas

## 🌈 Código do ZirohNeth auditado

- `src/Crypt/CryptHash.py`
- `src/Crypt/CryptBitcoin.py`
- `src/util/Electrum.py`
- `src/Site/Site.py`
- `src/Site/SiteManager.py`
- `src/Content/ContentManager.py`
- `src/Peer/PeerHashfield.py`

Repositório: https://github.com/FloflisPull/ZirohNeth

## 🌈 BLAKE e Multihash

- BLAKE3 specification: https://github.com/BLAKE3-team/BLAKE3-specs
- BLAKE3 official implementation: https://github.com/BLAKE3-team/BLAKE3
- BLAKE3 Rust crate: https://docs.rs/blake3/
- Python `hashlib` / BLAKE2: https://docs.python.org/3/library/hashlib.html
- Multihash: https://multiformats.io/multihash/
- Multicodec registry: https://github.com/multiformats/multicodec
- Kubo CLI: https://docs.ipfs.tech/reference/kubo/cli/
- Kubo configuration (`Import.HashFunction`): https://github.com/ipfs/kubo/blob/master/docs/config.md

## 🌈 Ethereum

- Ethereum accounts: https://ethereum.org/developers/docs/accounts/
- EIP-191: https://eips.ethereum.org/EIPS/eip-191
- EIP-712: https://eips.ethereum.org/EIPS/eip-712
- EIP-55: https://eips.ethereum.org/EIPS/eip-55
- ERC-1271: https://eips.ethereum.org/EIPS/eip-1271
- Python `eth-account`: https://eth-account.readthedocs.io/en/stable/
- Python `eth-utils`: https://eth-utils.readthedocs.io/
- Rust Alloy: https://docs.rs/alloy/latest/alloy/
- Alloy signer: https://docs.rs/alloy-signer/latest/alloy_signer/

## 🌈 Canonicalização

- RFC 8785 — JSON Canonicalization Scheme: https://www.rfc-editor.org/rfc/rfc8785
- Python `rfc8785`: https://pypi.org/project/rfc8785/
- Rust `serde_json_canonicalizer`: https://docs.rs/serde_json_canonicalizer/

---

# 🌈 13. Resultado esperado desta primeira etapa

Ao concluir esta trilha, ZirohNeth deverá ser capaz de:

- verificar sites Bitcoin antigos sem quebrar sua história;
- calcular e verificar novos hashes de conteúdo com identificadores explícitos;
- criar novos sites cujo endereço raiz seja uma identidade Ethereum;
- assinar e verificar manifests Ethereum usando EIP-712;
- relacionar uma identidade Bitcoin antiga a uma identidade Ethereum nova por provas cruzadas;
- apresentar o endereço de migração no site antigo;
- manter o site antigo legível e tratá-lo como histórico/read-only no protocolo novo;
- impedir rollback depois de um checkpoint terminal conhecido, com a política de descoberta de checkpoints documentada.

**Este estudo não declara essas capacidades implementadas.** O próximo trabalho é transformar as decisões pendentes em ADRs, gerar vetores de teste e implementar a compatibilidade em pequenas etapas, sem quebrar a rede legada.