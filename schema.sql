CREATE TABLE estados (
    uf VARCHAR(2) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    regiao VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE aliquotas_internas (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) REFERENCES estados(uf),
    aliquota DECIMAL(5,2) NOT NULL,
    fonte VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE aliquotas_interestaduais (
    id SERIAL PRIMARY KEY,
    uf_origem VARCHAR(2) REFERENCES estados(uf) NOT NULL,
    uf_destino VARCHAR(2) REFERENCES estados(uf) NOT NULL,
    aliquota DECIMAL(5,2) NOT NULL,
    fonte VARCHAR(50),
    data_extracao TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(uf_origem, uf_destino)
);

CREATE TABLE historico_atualizacoes (
    id SERIAL PRIMARY KEY,
    fonte VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'sucesso', 'erro', 'parcial'
    total_registros_inseridos INT DEFAULT 0,
    mensagem TEXT,
    data_extracao TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_aliq_inter ON aliquotas_interestaduais(uf_origem);
CREATE INDEX idx_aliq_inter_destino ON aliquotas_interestaduais(uf_destino);
CREATE INDEX idx_aliq_inter_ativo ON aliquotas_interestaduais(ativo);
CREATE INDEX idx_aliq_interna_uf ON aliquotas_internas(uf);
CREATE INDEX idx_aliq_interna_ativo ON aliquotas_internas(ativo);

ALTER TABLE estados ENABLE ROW LEVEL SECURITY;
ALTER TABLE aliquotas_internas ENABLE ROW LEVEL SECURITY;
ALTER TABLE aliquotas_interestaduais ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_atualizacoes ENABLE ROW LEVEL SECURITY;
