'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const grpc = require('@grpc/grpc-js');
const crypto = require('crypto');
const { connect, signers } = require('@hyperledger/fabric-gateway');

const defaultCryptoPath = path.join(
    os.homedir(),
    'fabric',
    'fabric-samples',
    'test-network',
    'organizations',
    'peerOrganizations',
    'org1.example.com'
);
const cryptoPath = process.env.FABRIC_CRYPTO_PATH || defaultCryptoPath;
const organization = process.env.FABRIC_ORGANIZATION || 'org1.example.com';
const channelName = process.env.FABRIC_CHANNEL_NAME || 'mychannel';
const chaincodeName = process.env.FABRIC_CHAINCODE_NAME || 'pharmaverse';
const mspId = process.env.FABRIC_MSP_ID || 'Org1MSP';
const peerEndpoint = process.env.FABRIC_PEER_ENDPOINT || 'localhost:7051';
const peerHostAlias =
    process.env.FABRIC_PEER_HOST_ALIAS || 'peer0.org1.example.com';
const connectionTimeoutMs = Number(
    process.env.FABRIC_CONNECTION_TIMEOUT_MS || 5000
);

function resolveIdentityPaths(basePath, org = 'org1.example.com') {
    const defaultOrganizationPath = path.join(
        basePath,
        'users',
        'Admin@' + org,
        'msp'
    );
    return {
        defaultOrganizationPath,
        certPath: path.join(
            defaultOrganizationPath,
            'signcerts',
            'cert.pem'
        ),
        keyDirectoryPath: path.join(defaultOrganizationPath, 'keystore'),
        tlsCertPath: path.join(
            basePath,
            'tlsca',
            'tlsca.' + org + '-cert.pem'
        )
    };
}

const identityPaths = resolveIdentityPaths(cryptoPath, organization);
const defaultOrganizationPath = identityPaths.defaultOrganizationPath;
const certPath = process.env.FABRIC_CERT_PATH || identityPaths.certPath;
const keyDirectoryPath = identityPaths.keyDirectoryPath;
const tlsCertPath = process.env.FABRIC_TLS_CERT_PATH || identityPaths.tlsCertPath;

function resolveDefaultKeyPath(directory) {
    try {
        const candidates = fs.readdirSync(directory)
            .filter(name => name.endsWith('_sk'));
        if (candidates.length === 1) {
            return path.join(directory, candidates[0]);
        }
    } catch {
        // Keep health available when Fabric identities are not mounted yet.
    }
    return path.join(directory, 'priv_sk');
}

const keyPath = process.env.FABRIC_KEY_PATH ||
    resolveDefaultKeyPath(keyDirectoryPath);

function createGrpcClient() {
    const tlsRootCert = fs.readFileSync(tlsCertPath);
    return new grpc.Client(
        peerEndpoint,
        grpc.credentials.createSsl(tlsRootCert),
        {
            'grpc.ssl_target_name_override': peerHostAlias
        }
    );
}

function createIdentity() {
    return {
        mspId,
        credentials: fs.readFileSync(certPath)
    };
}

function createSigner() {
    if (!keyPath) {
        throw new Error('FABRIC_KEY_PATH must identify a private key');
    }
    const privateKeyPem = fs.readFileSync(keyPath);
    return signers.newPrivateKeySigner(crypto.createPrivateKey(privateKeyPem));
}

function createContract() {
    const client = createGrpcClient();
    const gateway = connect({
        client,
        identity: createIdentity(),
        signer: createSigner(),
        evaluateOptions: () => ({
            deadline: Date.now() + connectionTimeoutMs
        })
    });
    const network = gateway.getNetwork(channelName);
    const contract = network.getContract(chaincodeName);
    return { client, gateway, contract };
}

async function evaluate(transactionName, ...args) {
    const { client, gateway, contract } = createContract();
    try {
        const result = await contract.evaluateTransaction(transactionName, ...args);
        return JSON.parse(Buffer.from(result).toString('utf8'));
    } finally {
        gateway.close();
        client.close();
    }
}

async function submit(transactionName, ...args) {
    const { client, gateway, contract } = createContract();
    try {
        const result = await contract.submitTransaction(transactionName, ...args);
        return JSON.parse(Buffer.from(result).toString('utf8'));
    } finally {
        gateway.close();
        client.close();
    }
}

const registerDrug = (drugId, name, strength, manufacturer) =>
    submit('registerDrug', drugId, name, strength, manufacturer);
const createBatch = (batchId, drugId, manufacturer, quantity, manufacturedDate, expiryDate, qrId, rfidId) => {
    const args = [batchId, drugId, manufacturer, quantity, manufacturedDate, expiryDate];
    args.push(qrId || '', rfidId || '');
    return submit('createBatch', ...args);
};
const assignIdentity = (batchId, qrId, rfidId) =>
    submit('assignIdentity', batchId, qrId, rfidId);
const recordIoTEvent = (batchId, shipmentId, temperature, humidity, latitude, longitude, movement, rfidId) =>
    submit('recordIoTEvent', batchId, shipmentId, temperature, humidity, latitude, longitude, movement, rfidId);
const recordAIAlert = (batchId, shipmentId, alertType, riskScore, explanation, detectedBy) =>
    submit('recordAIAlert', batchId, shipmentId, alertType, riskScore, explanation, detectedBy);
const flagDrug = (batchId, reason, riskLevel, flaggedBy) =>
    submit('flagDrug', batchId, reason, riskLevel, flaggedBy);
const shipDrug = (shipmentId, batchId, from, to, transporter) =>
    submit('shipDrug', shipmentId, batchId, from, to, transporter);
const receiveDrug = (shipmentId, receiver) =>
    submit('receiveDrug', shipmentId, receiver);
const transferDrug = (batchId, from, to) =>
    submit('transferDrug', batchId, from, to);

function getDrug(drugId) {
    return evaluate('getDrug', drugId);
}

function getBatch(batchId) {
    return evaluate('getBatch', batchId);
}

function verifyIdentity(batchId, qrId, rfidId) {
    return evaluate('verifyIdentity', batchId, qrId, rfidId);
}

function getShipment(shipmentId) {
    return evaluate('getShipment', shipmentId);
}

function getFlag(flagId) {
    return evaluate('getFlag', flagId);
}

function getIoTEvent(eventId) {
    return evaluate('getIoTEvent', eventId);
}

function getAIAlert(alertId) {
    return evaluate('getAIAlert', alertId);
}

function getBatchHistory(batchId) {
    return evaluate('getBatchHistory', batchId);
}

module.exports = {
    getDrug,
    getBatch,
    verifyIdentity,
    getShipment,
    getFlag,
    getIoTEvent,
    getAIAlert,
    getBatchHistory,
    registerDrug,
    createBatch,
    assignIdentity,
    recordIoTEvent,
    recordAIAlert,
    flagDrug,
    shipDrug,
    receiveDrug,
    transferDrug,
    resolveIdentityPaths,
    config: {
        cryptoPath,
        channelName,
        chaincodeName,
        mspId,
        peerEndpoint,
        peerHostAlias,
        certPath,
        keyPath,
        tlsCertPath,
        connectionTimeoutMs
    }
};
