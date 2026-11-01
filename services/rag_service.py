"""
IncluSign AI — Serviço RAG (Retrieval-Augmented Generation)
===========================================================
Pipeline completo atualizado para usar o motor vetorial QDRANT.
Garante alta resiliência no Windows e compatibilidade com Numpy 2.0+

Requisitos atendidos: RNF-002 (offline), estratégia do Documento 7.
"""

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

import pymupdf as fitz

from config import (
    BASE_DIR,
    EMBEDDING_MODEL,
    KNOWLEDGE_DIR,
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_SIZE,
    RAG_TOP_K,
    SAMPLE_KNOWLEDGE_DIR,
    VECTOR_COLLECTION,
    VECTOR_DB_DIR,
)

logger = logging.getLogger(__name__)


class RAGService:
    """Serviço de Retrieval-Augmented Generation (RAG) integrado ao banco vetorial Qdrant."""

    def __init__(self):
        self.available = False
        self.doc_count = 0
        self.chunk_count = 0
        self._client = None
        self._embedder = None
        self._initialized = False
        self._init_message = ""

        self._initialize()

    def _process_new_pdfs(self):
        """Verifica novos arquivos PDF, executa extração textual e move para o repositório de processados."""
        from services.text_processor import (
            TextProcessor,  # Importação dinâmica do processador textual
        )

        raw_dir = BASE_DIR / "pdfs_brutos"
        processed_dir = BASE_DIR / "pdfs_processados"

        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        pdf_files = list(raw_dir.glob("*.pdf"))
        if not pdf_files:
            return

        logger.info(
            f"Automação: {len(pdf_files)} novos PDFs encontrados. Iniciando extração estrutural..."
        )

        for pdf_path in pdf_files:
            txt_name = pdf_path.with_suffix(".txt").name
            txt_path_dest = KNOWLEDGE_DIR / txt_name

            try:
                # 1. Extração estrutural por blocos com ordenação espacial de colunas
                document = fitz.open(str(pdf_path))
                raw_blocks = []

                for page in document:
                    # O sinalizador TEXT_DEHYPHENATE une hifens automaticamente
                    # "blocks" extrai a estrutura lógica da página
                    blocks = page.get_text("blocks", flags=fitz.TEXT_DEHYPHENATE)

                    # Ordenação nativa por leitura top-down / colunas
                    blocks.sort(key=lambda b: (b[1], b[0]))

                    for b in blocks:
                        if b[6] == 0:  # Apenas blocos de texto
                            raw_blocks.append(b[4])
                document.close()

                # 2. Higienização e normalização do texto extraído
                clean_full_text = TextProcessor.clean_extracted_blocks(raw_blocks)

                # 3. Persistência do texto normalizado na base de conhecimento
                with open(str(txt_path_dest), "w", encoding="utf-8") as f:
                    f.write(clean_full_text)

                # 4. Realocação do PDF original para a pasta de processados
                destination = processed_dir / pdf_path.name
                if destination.exists():
                    destination.unlink()
                shutil.move(str(pdf_path), str(destination))

                logger.info(
                    f"Sucesso: {pdf_path.name} convertido com segurança e movido para pdfs_processados."
                )

            except Exception as exc:
                logger.error(f"Erro ao converter {pdf_path.name}: {exc}")

    def _initialize(self):
        try:
            KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
            VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

            self._process_new_pdfs()

            txt_files = list(KNOWLEDGE_DIR.glob("*.txt"))

            # Fallback transparente para dados de demonstração públicos
            if not txt_files and SAMPLE_KNOWLEDGE_DIR.exists():
                txt_files = list(SAMPLE_KNOWLEDGE_DIR.glob("*.txt"))
                if txt_files:
                    logger.info(
                        "Base local vazia. Inicializando RAG com dataset demonstrativo (sample_knowledge)."
                    )

            self.doc_count = len(txt_files)

            if self.doc_count == 0:
                self._init_message = (
                    "Módulo RAG ativo, mas nenhum documento inserido. "
                    "Adicione arquivos .txt em: " + str(KNOWLEDGE_DIR)
                )
                logger.info(self._init_message)
                self._try_load_existing_collection()
                return

            self._setup_qdrant()

            # Verificação de persistência prévia na coleção para evitar reindexação redundante
            try:
                self.chunk_count = self._client.count(collection_name=VECTOR_COLLECTION).count
                if self.chunk_count > 0:
                    self.available = True
                    self._init_message = (
                        f"RAG carregado do cache Qdrant: {self.chunk_count} trechos."
                    )
                    logger.info(self._init_message)
                    return
            except Exception:
                pass

            self._ingest_documents(txt_files)

            self.available = True
            self._init_message = (
                f"RAG inicializado: {self.doc_count} documento(s), {self.chunk_count} trecho(s)."
            )
            logger.info(self._init_message)

        except ImportError as exc:
            self._init_message = "Bibliotecas do Qdrant ausentes."
            logger.warning("RAG indisponível (import): %s", exc)
        except Exception as exc:
            self._init_message = "Erro ao inicializar Qdrant."
            logger.error("Erro no RAG (Qdrant): %s", exc, exc_info=True)

    def _try_load_existing_collection(self):
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(path=str(VECTOR_DB_DIR))

            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(EMBEDDING_MODEL)

            self.chunk_count = self._client.count(collection_name=VECTOR_COLLECTION).count
            if self.chunk_count > 0:
                self.available = True
                self._init_message = (
                    f"RAG carregado: {self.chunk_count} trechos da sessão anterior."
                )
                logger.info(self._init_message)
        except Exception as exc:
            logger.debug("Sem coleção no Qdrant: %s", exc)

    def _setup_qdrant(self):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        from sentence_transformers import SentenceTransformer

        if self._embedder is None:
            logger.info("Carregando modelo SentenceTransformer...")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)

        self._client = QdrantClient(path=str(VECTOR_DB_DIR))

        collections_response = self._client.get_collections()
        col_names = [c.name for c in collections_response.collections]

        if VECTOR_COLLECTION not in col_names:
            self._client.create_collection(
                collection_name=VECTOR_COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def _ingest_documents(self, txt_files: list[Path]):
        from qdrant_client.models import PointStruct

        all_chunks = []
        all_metadatas = []

        for txt_path in txt_files:
            try:
                with open(str(txt_path), encoding="utf-8") as f:
                    full_text = f.read()

                if not full_text.strip():
                    continue

                chunks = self._chunk_text(full_text)
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_metadatas.append({"source": txt_path.name, "chunk_index": i, "text": chunk})
            except Exception as exc:
                logger.error("Erro TXT '%s': %s", txt_path.name, exc)
                continue

        if all_chunks:
            logger.info(f"Gerando embeddings para {len(all_chunks)} trechos (aguarde)...")
            vectors = self._embedder.encode(all_chunks).tolist()

            points = []
            for i in range(len(all_chunks)):
                hash_id = hashlib.md5(f"{all_metadatas[i]['source']}_{i}".encode()).hexdigest()
                point_id = str(uuid.UUID(hash_id[:32]))

                points.append(PointStruct(id=point_id, vector=vectors[i], payload=all_metadatas[i]))

            batch_size = 100
            for start in range(0, len(points), batch_size):
                end = start + batch_size
                self._client.upsert(collection_name=VECTOR_COLLECTION, points=points[start:end])

            self.chunk_count = self._client.count(collection_name=VECTOR_COLLECTION).count

    def _chunk_text(self, text: str) -> list[str]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        # 1. Segmentação estruturada específica para dicionários terminológicos
        if cleaned_text.count("TERMO TÉCNICO:") > 5:
            parts = cleaned_text.split("TERMO TÉCNICO:")
            generated_chunks = []

            header = parts[0].strip()
            if header and len(header) > 20:
                generated_chunks.append(header)

            for part in parts[1:]:
                chunk = "TERMO TÉCNICO:" + part
                if len(chunk.strip()) > 20:
                    generated_chunks.append(chunk.strip())

            return generated_chunks

        # 2. Segmentação textual padrão com janela deslizante para artigos e manuais pedagógicos
        paragraphs = [
            paragraph.strip() for paragraph in cleaned_text.split("\n") if paragraph.strip()
        ]

        generated_chunks = []
        current_chunk_paragraphs = []
        current_chunk_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            # Tratamento para parágrafos excepcionalmente grandes
            if paragraph_length > RAG_CHUNK_SIZE:
                if current_chunk_paragraphs:
                    generated_chunks.append(" ".join(current_chunk_paragraphs))
                    current_chunk_paragraphs = []
                    current_chunk_length = 0

                start_index = 0
                while start_index < paragraph_length:
                    end_index = start_index + RAG_CHUNK_SIZE
                    if end_index < paragraph_length:
                        safe_break_point = paragraph.rfind(
                            ". ", start_index + (RAG_CHUNK_SIZE // 2), end_index
                        )
                        if safe_break_point == -1:
                            safe_break_point = paragraph.rfind(
                                " ", start_index + (RAG_CHUNK_SIZE // 2), end_index
                            )
                        if safe_break_point != -1:
                            end_index = safe_break_point + 1

                    chunk_segment = paragraph[start_index:end_index].strip()
                    if chunk_segment:
                        generated_chunks.append(chunk_segment)

                    start_index = end_index - RAG_CHUNK_OVERLAP
                    if start_index < 0:
                        start_index = 0
                continue

            # Agrupamento dinâmico de parágrafos normais
            space_separator_length = 1 if current_chunk_length > 0 else 0
            if (current_chunk_length + paragraph_length + space_separator_length) <= RAG_CHUNK_SIZE:
                current_chunk_paragraphs.append(paragraph)
                current_chunk_length += paragraph_length + space_separator_length
            else:
                generated_chunks.append(" ".join(current_chunk_paragraphs))
                overlap_paragraphs = []
                overlap_length = 0
                for previous_paragraph in reversed(current_chunk_paragraphs):
                    if (overlap_length + len(previous_paragraph)) <= RAG_CHUNK_OVERLAP:
                        overlap_paragraphs.insert(0, previous_paragraph)
                        overlap_length += len(previous_paragraph) + 1
                    else:
                        break
                current_chunk_paragraphs = overlap_paragraphs + [paragraph]
                total_characters = sum(len(para) for para in current_chunk_paragraphs)
                total_spaces = max(0, len(current_chunk_paragraphs) - 1)
                current_chunk_length = total_characters + total_spaces

        if current_chunk_paragraphs:
            final_chunk = " ".join(current_chunk_paragraphs)
            if not generated_chunks or generated_chunks[-1] != final_chunk:
                generated_chunks.append(final_chunk)

        return generated_chunks

    # ------------------------------------------------------------------
    # Interface Pública
    # ------------------------------------------------------------------

    def query(self, question: str, top_k: int | None = None) -> list[dict]:
        if not self.available or self._client is None or self._embedder is None:
            return []

        if top_k is None:
            top_k = RAG_TOP_K

        try:
            query_vector = self._embedder.encode(question).tolist()
            search_result = self._client.query_points(
                collection_name=VECTOR_COLLECTION,
                query=query_vector,
                limit=min(top_k, self.chunk_count),
            ).points

            context_items = []
            for hit in search_result:
                context_items.append(
                    {
                        "text": hit.payload.get("text", ""),
                        "source": hit.payload.get("source", "Desconhecido"),
                        "score": round(hit.score, 4),
                    }
                )
            return context_items
        except Exception as exc:
            logger.error("Erro na consulta Qdrant RAG: %s", exc)
            return []

    def reindex(self) -> dict:
        try:
            if self._client is not None:
                self._client.delete_collection(VECTOR_COLLECTION)
            self._initialized = False
            self.available = False
            self.chunk_count = 0
            self._initialize()
            return {
                "success": True,
                "message": self._init_message,
                "documentos": self.doc_count,
                "trechos": self.chunk_count,
            }
        except Exception as exc:
            logger.error("Erro ao re-indexar: %s", exc)
            return {"success": False, "message": f"Erro: {exc}", "documentos": 0, "trechos": 0}

    def get_status(self) -> dict:
        return {
            "disponivel": self.available,
            "documentos": self.doc_count,
            "trechos_indexados": self.chunk_count,
            "pasta_conhecimento": str(KNOWLEDGE_DIR),
            "mensagem": self._init_message,
        }
