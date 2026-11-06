'use strict';

const assert = require('assert');
const http = require('http');
const test = require('node:test');

process.env.FABRIC_GATEWAY_SECRET = 'test-secret';
const { createServer, configuredPort } = require('../httpServer');
const fabric = require('../fabricService');
const path = require('path');

function request(server, method, path, body) {
    return new Promise((resolve, reject) => {
        const address = server.address();
        const request = http.request({
            host: '127.0.0.1',
            port: address.port,
            path,
            method,
            headers: {
                'X-PharmaVerse-Service-Secret': 'test-secret',
                ...(body ? { 'Content-Type': 'application/json' } : {})
            }
        }, response => {
            let data = '';
            response.on('data', chunk => data += chunk);
            response.on('end', () => resolve({
                status: response.statusCode,
                body: JSON.parse(data)
            }));
        });
        request.on('error', reject);
        if (body) request.write(body);
        request.end();
    });
}

function listen(server) {
    return new Promise(resolve => {
        server.listen(0, '127.0.0.1', resolve);
    });
}

function close(server) {
    return new Promise(resolve => server.close(resolve));
}

test('health endpoint is available without Fabric', async () => {
    const server = createServer();
    await listen(server);
    const result = await request(server, 'GET', '/health');
    assert.equal(result.status, 200);
    assert.equal(result.body.data.status, 'ok');
    await close(server);
});

test('unknown operation is rejected', async () => {
    const server = createServer();
    await listen(server);
    const result = await request(server, 'GET', '/api/unknown');
    assert.equal(result.status, 404);
    assert.equal(result.body.error.code, 'NOT_FOUND');
    await close(server);
});

test('malformed verify request is rejected', async () => {
    const server = createServer();
    await listen(server);
    const result = await request(server, 'POST', '/api/verify-identity', '{');
    assert.equal(result.status, 400);
    assert.equal(result.body.error.code, 'INVALID_REQUEST');
    await close(server);
});

test('write endpoint forwards only a named operation and real transaction data', async () => {
    const original = fabric.registerDrug;
    fabric.registerDrug = async () => ({
        drugId: 'DRUG-2026-000001',
        transactionId: 'fabric-tx-1'
    });
    const server = createServer();
    await listen(server);
    const result = await request(
        server,
        'POST',
        '/api/drugs/register',
        JSON.stringify({
            drugId: 'DRUG-2026-000001',
            name: 'Example',
            strength: '10mg',
            manufacturer: 'Example Labs'
        })
    );
    assert.equal(result.status, 200);
    assert.equal(result.body.data.transactionId, 'fabric-tx-1');
    fabric.registerDrug = original;
    await close(server);
});

test('batch creation forwards a supplied QR/RFID pair to chaincode', async () => {
    const original = fabric.createBatch;
    let captured;
    fabric.createBatch = async (...args) => {
        captured = args;
        return { batchId: args[0], transactionId: 'fabric-tx-batch' };
    };
    const server = createServer();
    try {
        await listen(server);
        const result = await request(server, 'POST', '/api/batches/create', JSON.stringify({
            batchId: 'BATCH-1', drugId: 'DRUG-1', manufacturer: 'Example Labs',
            quantity: 2, manufacturedDate: '2026-01-01', expiryDate: '2028-01-01',
            qrId: 'QR-EXISTING-1', rfidId: 'RFID-EXISTING-1'
        }));
        assert.equal(result.status, 200);
        assert.deepEqual(captured, [
            'BATCH-1', 'DRUG-1', 'Example Labs', '2', '2026-01-01', '2028-01-01',
            'QR-EXISTING-1', 'RFID-EXISTING-1'
        ]);
    } finally {
        fabric.createBatch = original;
        await close(server);
    }
});

test('write endpoint rejects a missing service secret', async () => {
    const server = createServer();
    await listen(server);
    const result = await new Promise((resolve, reject) => {
        const address = server.address();
        const request = http.request({
            host: '127.0.0.1',
            port: address.port,
            path: '/api/drugs/register',
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }, response => {
            let data = '';
            response.on('data', chunk => data += chunk);
            response.on('end', () => resolve({
                status: response.statusCode, body: JSON.parse(data)
            }));
        });
        request.on('error', reject);
        request.write('{}');
        request.end();
    });
    assert.equal(result.status, 401);
    await close(server);
});

test('unconfigured service secret is reported as configuration failure', async () => {
    const modulePath = require.resolve('../httpServer');
    const configuredModule = require.cache[modulePath];
    const configuredSecret = process.env.FABRIC_GATEWAY_SECRET;
    delete process.env.FABRIC_GATEWAY_SECRET;
    delete require.cache[modulePath];
    const { createServer: createUnconfiguredServer } = require('../httpServer');
    if (configuredSecret === undefined) {
        delete process.env.FABRIC_GATEWAY_SECRET;
    } else {
        process.env.FABRIC_GATEWAY_SECRET = configuredSecret;
    }
    require.cache[modulePath] = configuredModule;

    const server = createUnconfiguredServer();
    try {
        await listen(server);
        const result = await request(server, 'POST', '/api/drugs/register', '{}');
        assert.equal(result.status, 503);
        assert.equal(result.body.error.code, 'SERVICE_NOT_CONFIGURED');
    } finally {
        await close(server);
    }
});

test('missing ledger assets are distinct from gateway failures', async () => {
    const original = fabric.getBatch;
    fabric.getBatch = async () => {
        throw new Error('Batch BATCH-MISSING does not exist');
    };
    const server = createServer();
    try {
        await listen(server);
        const result = await request(server, 'GET', '/api/batches/BATCH-MISSING');
        assert.equal(result.status, 404);
        assert.equal(result.body.success, false);
        assert.equal(result.body.error.code, 'ASSET_NOT_FOUND');
    } finally {
        fabric.getBatch = original;
        await close(server);
    }
});

test('Fabric transport failures remain unavailable errors', async () => {
    const original = fabric.getBatch;
    fabric.getBatch = async () => {
        throw new Error('connect ECONNREFUSED');
    };
    const server = createServer();
    try {
        await listen(server);
        const result = await request(server, 'GET', '/api/batches/BATCH-1');
        assert.equal(result.status, 502);
        assert.equal(result.body.success, false);
        assert.equal(result.body.error.code, 'FABRIC_UNAVAILABLE');
    } finally {
        fabric.getBatch = original;
        await close(server);
    }
});

test('gateway defaults to the backend port and honors an explicit override', () => {
    assert.equal(configuredPort({}), 8090);
    assert.equal(configuredPort({ FABRIC_GATEWAY_PORT: '8081' }), 8081);
});

test('Fabric identity paths use the configured root and standard certificate filename', () => {
    const root = path.join(path.sep, 'fixture', 'peerOrganizations', 'org1.example.com');
    const paths = fabric.resolveIdentityPaths(root);
    assert.equal(paths.certPath, path.join(
        root, 'users', 'Admin@org1.example.com', 'msp', 'signcerts', 'cert.pem'
    ));
    assert.equal(paths.keyDirectoryPath, path.join(
        root, 'users', 'Admin@org1.example.com', 'msp', 'keystore'
    ));
    assert.equal(paths.tlsCertPath, path.join(
        root, 'tlsca', 'tlsca.org1.example.com-cert.pem'
    ));
});
