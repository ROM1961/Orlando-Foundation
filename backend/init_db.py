import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}@{os.environ['PGHOST']}/{os.environ['PGDATABASE']}?sslmode={os.environ['PGSSLMODE']}"

async def init_database():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create protocol_configs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS protocol_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                protocol_name VARCHAR(100) NOT NULL,
                network VARCHAR(50) NOT NULL,
                contract_type VARCHAR(50) NOT NULL,
                contract_address VARCHAR(42) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(protocol_name, network, contract_type)
            )
        """)
        
        # Create custom_tokens table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token_symbol VARCHAR(10) NOT NULL,
                token_name VARCHAR(100) NOT NULL,
                token_address VARCHAR(42) UNIQUE NOT NULL,
                decimals INTEGER NOT NULL,
                total_supply DECIMAL(30, 0),
                network VARCHAR(50) NOT NULL,
                price_feed_address VARCHAR(42),
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create user_vaults table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_vaults (
                id UUID PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                vault_address VARCHAR(42) UNIQUE NOT NULL,
                owner_addresses TEXT[],
                network VARCHAR(50) NOT NULL,
                vault_type VARCHAR(50) NOT NULL,
                label VARCHAR(255),
                private_key_encrypted BYTEA NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create vault_positions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_positions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vault_id UUID NOT NULL REFERENCES user_vaults(id) ON DELETE CASCADE,
                protocol_name VARCHAR(100) NOT NULL,
                position_type VARCHAR(50) NOT NULL,
                token_address VARCHAR(42) NOT NULL,
                token_symbol VARCHAR(10) NOT NULL,
                amount DECIMAL(30, 18) NOT NULL,
                apy DECIMAL(8, 4),
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(vault_id, protocol_name, position_type, token_address)
            )
        """)
        
        # Create vault_transactions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_transactions (
                id UUID PRIMARY KEY,
                vault_id UUID NOT NULL REFERENCES user_vaults(id) ON DELETE CASCADE,
                tx_hash VARCHAR(66) UNIQUE NOT NULL,
                protocol_name VARCHAR(100),
                action VARCHAR(50) NOT NULL,
                token_address VARCHAR(42),
                amount DECIMAL(30, 18),
                gas_used DECIMAL(30, 0),
                status VARCHAR(20) NOT NULL,
                block_number INTEGER,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create vault_health table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_health (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vault_id UUID NOT NULL REFERENCES user_vaults(id) ON DELETE CASCADE,
                protocol_name VARCHAR(100) NOT NULL,
                health_factor DECIMAL(18, 8),
                total_collateral_usd DECIMAL(30, 2),
                total_debt_usd DECIMAL(30, 2),
                ltv_ratio DECIMAL(8, 4),
                liquidation_threshold DECIMAL(8, 4),
                alert_sent BOOLEAN DEFAULT FALSE,
                checked_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Insert protocol configs
        await conn.execute("""
            INSERT INTO protocol_configs (protocol_name, network, contract_type, contract_address, is_active)
            VALUES 
                ('Aave', 'ethereum', 'pool', '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2', TRUE),
                ('Compound', 'ethereum', 'comet', '0xA17581A9E3356d9A858b789D68B4d866e593aE94', TRUE)
            ON CONFLICT (protocol_name, network, contract_type) DO NOTHING
        """)
        
        # Insert ACS token
        await conn.execute("""
            INSERT INTO custom_tokens (token_symbol, token_name, token_address, decimals, total_supply, network, is_verified)
            VALUES ('ACS', 'ACS Token', '0x0000000000000000000000000000000000000000', 18, 1000000000, 'ethereum', TRUE)
            ON CONFLICT (token_address) DO NOTHING
        """)
        
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_database())