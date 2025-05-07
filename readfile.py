#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para ler e imprimir conteúdo de um arquivo CSV armazenado no Google Cloud Storage.
Este script é executado via GitHub Actions.
"""

import os
import json
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_gcp_credentials():
    """Configura as credenciais do GCP a partir da variável de ambiente."""
    try:
        # Obtém as credenciais da variável de ambiente
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        
        if not credentials_json:
            raise ValueError("Variável de ambiente GOOGLE_CREDENTIALS não encontrada")
        
        # Escreve as credenciais em um arquivo temporário
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        
        return credentials
    
    except Exception as e:
        logger.error(f"Erro ao configurar credenciais GCP: {e}")
        raise

def read_csv_from_gcs(bucket_name, file_path, credentials):
    """
    Lê um arquivo CSV do Google Cloud Storage e retorna um DataFrame.
    
    Args:
        bucket_name (str): Nome do bucket GCS
        file_path (str): Caminho para o arquivo CSV no bucket
        credentials: Credenciais GCP
        
    Returns:
        pandas.DataFrame: DataFrame contendo os dados do CSV
    """
    try:
        # Inicializa o cliente do GCS
        client = storage.Client(credentials=credentials)
        
        # Acessa o bucket
        bucket = client.bucket(bucket_name)
        
        # Obtém o blob (arquivo)
        blob = bucket.blob(file_path)
        
        logger.info(f"Baixando arquivo {file_path} do bucket {bucket_name}")
        
        # Download do conteúdo do arquivo para memória
        content = blob.download_as_string()
        
        # Converte o conteúdo para DataFrame
        df = pd.read_csv(pd.io.common.BytesIO(content))
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao ler arquivo CSV do GCS: {e}")
        raise

def main():
    """Função principal que executa o script."""
    try:
        # Configurações do bucket e arquivo
        # Substitua pelos valores corretos do seu projeto
        BUCKET_NAME = "calendar_sync"  # Substitua pelo nome do seu bucket
        FILE_PATH = "events_cache.csv"  # Substitua pelo caminho do arquivo
        
        # Configurar credenciais
        credentials = setup_gcp_credentials()
        
        # Ler o arquivo CSV
        logger.info("Iniciando leitura do arquivo CSV")
        df = read_csv_from_gcs(BUCKET_NAME, FILE_PATH, credentials)
        
        # Imprimir informações sobre o DataFrame
        logger.info(f"Arquivo CSV lido com sucesso. Dimensões: {df.shape}")
        
        # Imprimir as primeiras linhas do DataFrame
        print("Primeiras linhas do arquivo CSV:")
        print(df.head())
        
        # Imprimir estatísticas básicas
        print("\nEstatísticas básicas:")
        print(df.describe())
        
        # Imprimir informações sobre os tipos de dados
        print("\nTipos de dados:")
        print(df.dtypes)
        
        logger.info("Processamento concluído com sucesso")
        
    except Exception as e:
        logger.error(f"Erro durante a execução do script: {e}")
        raise

if __name__ == "__main__":
    main()