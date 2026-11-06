'use strict';

const fs = require('fs');
const grpc = require('@grpc/grpc-js');
const crypto = require('crypto');
const { connect, signers } = require('@hyperledger/fabric-gateway');

const CHANNEL_NAME = 'mychannel';
const CHAINCODE_NAME = 'pharmaverse';

const cryptoPath =
    process.env.FABRIC_CRYPTO_PATH ||
    '/home/pharma/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com';

const certPath =
    `${cryptoPath}/users/Admin@org1.example.com/msp/signcerts/Admin@org1.example.com-cert.pem`;

const keyDirectoryPath =
    `${cryptoPath}/users/Admin@org1.example.com/msp/keystore`;

const tlsCertPath =
    '/home/pharma/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem';

const peerEndpoint =
    process.env.FABRIC_PEER_ENDPOINT || 'localhost:7051';

const peerHostAlias =
    process.env.FABRIC_PEER_HOST_ALIAS || 'peer0.org1.example.com';


function newGrpcConnection() {
    const tlsRootCert = fs.readFileSync(tlsCertPath);

    const tlsCredentials = grpc.credentials.createSsl(tlsRootCert);

    return new grpc.Client(
        peerEndpoint,
        tlsCredentials,
        {
            'grpc.ssl_target_name_override': peerHostAlias
        }
    );
}


function newIdentity() {
    const credentials = fs.readFileSync(certPath);

    return {
        mspId: 'Org1MSP',
        credentials
    };
}


function newSigner() {
    const files = fs.readdirSync(keyDirectoryPath);

    if (files.length === 0) {
        throw new Error('No private key found in Fabric keystore');
    }

    const keyPath = `${keyDirectoryPath}/${files[0]}`;
    const privateKeyPem = fs.readFileSync(keyPath);

    const privateKey = crypto.createPrivateKey(privateKeyPem);

    return signers.newPrivateKeySigner(privateKey);
}


async function main() {
    const client = newGrpcConnection();

    const gateway = connect({
        client,
        identity: newIdentity(),
        signer: newSigner(),
        evaluateOptions: () => {
            return {
                deadline: Date.now() + 5000
            };
        },
        endorseOptions: () => {
            return {
                deadline: Date.now() + 15000
            };
        },
        submitOptions: () => {
            return {
                deadline: Date.now() + 15000
            };
        },
        commitStatusOptions: () => {
            return {
                deadline: Date.now() + 60000
            };
        }
    });

    const network = gateway.getNetwork(CHANNEL_NAME);
    const contract = network.getContract(CHAINCODE_NAME);

    console.log('========================================');
    console.log(' PharmaVerse Fabric Gateway');
    console.log('========================================');
    console.log(`Channel: ${CHANNEL_NAME}`);
    console.log(`Chaincode: ${CHAINCODE_NAME}`);
    console.log(`Peer: ${peerEndpoint}`);
    console.log('Fabric Gateway connected successfully.');

    const drugId = 'PARACETAMOL-500';

    try {
        const result = await contract.evaluateTransaction(
            'getDrug',
            drugId
        );

        console.log('Test query successful:');
        console.log(Buffer.from(result).toString("utf8"));
    } catch (error) {
        console.error('Fabric query failed:');
        console.error(error);
    }

    process.on('SIGINT', () => {
        gateway.close();
        client.close();
        process.exit(0);
    });

    process.on('SIGTERM', () => {
        gateway.close();
        client.close();
        process.exit(0);
    });
}


main().catch((error) => {
    console.error('Gateway startup failed:');
    console.error(error);
    process.exit(1);
});
