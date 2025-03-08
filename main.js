require('dotenv').config();
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const puppeteer = require('puppeteer');
const { ethers } = require('ethers');

class StorageScanAutomation {
    constructor() {
        if (!process.env.WALLET_PRIVATE_KEY) {
            throw new Error('WALLET_PRIVATE_KEY not found in .env file');
        }

        try {
            this.rpcUrls = JSON.parse(process.env.RPC_URLS);
        } catch (error) {
            console.log('Error parsing RPC_URLS, using default');
            this.rpcUrls = [
                'https://evmrpc-testnet.0g.ai',
                'https://og-testnet-evm.itrocket.net',
                'https://lightnode-json-rpc-0g.grandvalleys.com',
                'https://0g-json-rpc-public.originstake.com'
            ];
        }

        // Initialize provider with failover
        this.provider = this.setupProviderWithFailover();
        
        // Set up wallet
        try {
            this.wallet = new ethers.Wallet(process.env.WALLET_PRIVATE_KEY, this.provider);
        } catch (error) {
            throw new Error('Failed to initialize wallet: ' + error.message);
        }

        // Chain details
        this.chainId = '0x40d8'; // 16600
        this.networkName = '0G Chain Testnet';
        this.symbol = 'A0GI';
        this.decimals = 18;

        // Setup directories
        this.projectDir = process.cwd();
        this.downloadDir = path.join(this.projectDir, 'temp_images');
        this.setupDirectories();
    }

    setupProviderWithFailover() {
        // Create providers array
        const providers = this.rpcUrls.map(url => {
            const provider = new ethers.providers.JsonRpcProvider(url);
            // Configure provider
            provider.getNetwork = async () => ({
                chainId: 16600,
                name: '0G Chain Testnet'
            });
            return provider;
        });
        
        // Create failover provider with all RPCs
        return new ethers.providers.FallbackProvider(providers.map((provider, index) => ({
            provider,
            priority: index,
            stallTimeout: 1000
        })));
    }

    setupDirectories() {
        if (fs.existsSync(this.downloadDir)) {
            fs.rmSync(this.downloadDir, { recursive: true });
        }
        fs.mkdirSync(this.downloadDir);
    }

    cleanupImages() {
        if (fs.existsSync(this.downloadDir)) {
            fs.rmSync(this.downloadDir, { recursive: true });
        }
    }

    async initBrowser() {
        this.browser = await puppeteer.launch({
            headless: false,
            defaultViewport: null,
            args: ['--start-maximized']
        });

        // Create new page and inject wallet
        this.page = await this.browser.newPage();

        // Set longer default timeout
        this.page.setDefaultTimeout(60000);

        // Inject wallet data before page loads
        await this.page.evaluateOnNewDocument((walletData) => {
            window.ethereum = {
                isMetaMask: true,
                request: async ({ method, params }) => {
                    switch (method) {
                        case 'eth_requestAccounts':
                        case 'eth_accounts':
                            return [walletData.address];
                        case 'eth_chainId':
                            return walletData.chainId;
                        case 'net_version':
                            return '16600';
                        case 'eth_getBalance':
                            return '0x1000000000000000000';
                        case 'wallet_addEthereumChain':
                            return null;
                        case 'wallet_switchEthereumChain':
                            if (params[0].chainId === walletData.chainId) {
                                return null;
                            }
                            throw new Error('User rejected the request.');
                        case 'eth_signTypedData_v4':
                        case 'personal_sign':
                            return '0x0000000000000000000000000000000000000000000000000000000000000000';
                        default:
                            console.log('Method called:', method, params);
                            return null;
                    }
                },
                on: (eventName, callback) => {
                    if (eventName === 'accountsChanged') {
                        callback([walletData.address]);
                    }
                    if (eventName === 'chainChanged') {
                        callback(walletData.chainId);
                    }
                },
                removeListener: () => {},
                isConnected: () => true,
                chainId: walletData.chainId,
                networkVersion: '16600',
                selectedAddress: walletData.address,
                enable: async () => [walletData.address]
            };

            window.web3 = {
                currentProvider: window.ethereum
            };
        }, {
            address: this.wallet.address,
            chainId: this.chainId,
        });
    }

    async connectWallet() {
        // Navigate to the website
        await this.page.goto('https://storagescan-newton.0g.ai/tool');
        
        console.log('\n⌛ Please connect your wallet manually in the browser window.');
        console.log('Once connected, the file upload area should be visible.');
        console.log('Press Enter in terminal to continue...');
        
        // Wait for user to press Enter
        await this.promptUser('');

        try {
            // Wait for the file input label to appear (indicates successful connection)
            await this.page.waitForSelector('.sc-aXZVg.kGRXWn', { 
                visible: true,
                timeout: 10000 
            });

            console.log('✓ File upload area detected, proceeding with uploads...\n');

        } catch (error) {
            console.log('\n❌ Could not detect file upload area. Please verify wallet connection.');
            console.log('Would you like to:');
            console.log('1. Try detecting again');
            console.log('2. Continue anyway');
            console.log('3. Abort process');
            
            const choice = await this.promptUser('Enter choice (1-3): ');
            
            switch(choice) {
                case '1':
                    return await this.connectWallet();
                case '2':
                    console.log('\n⚠️  Proceeding without verification...');
                    break;
                default:
                    throw new Error('Process aborted by user');
            }
        }
    }

    async downloadRandomImages(numImages) {
        console.log(`\nDownloading ${numImages} random images...`);
        const images = [];
        const retryCount = 3;

        for (let i = 0; i < numImages; i++) {
            let success = false;
            for (let attempt = 0; attempt < retryCount; attempt++) {
                try {
                    console.log(`Downloading image ${i + 1}/${numImages}...`);
                    const imageUrl = `https://picsum.photos/800/600?random=${i}`;
                    const response = await axios({
                        method: 'get',
                        url: imageUrl,
                        responseType: 'arraybuffer',
                        timeout: 10000,
                        headers: { 'User-Agent': 'Mozilla/5.0' }
                    });

                    const filePath = path.join(this.downloadDir, `image_${i}.jpg`);
                    fs.writeFileSync(filePath, response.data);
                    images.push(filePath);
                    console.log(`✓ Image ${i + 1} downloaded successfully`);
                    success = true;
                    break;
                } catch (error) {
                    console.log(`⚠️  Attempt ${attempt + 1}: Error downloading image ${i + 1}: ${error.message}`);
                    if (attempt === retryCount - 1) {
                        console.log(`❌ Failed to download image ${i + 1} after ${retryCount} attempts`);
                    }
                }
            }

            if (!success) {
                const retry = await this.promptUser('Enter "r" to retry this image, or any other key to continue: ');
                if (retry.toLowerCase() === 'r') {
                    i--;
                    continue;
                }
            }
        }

        return images;
    }

    async uploadImages(imagePaths) {
        console.log('\n🚀 Starting Upload Process\n');

        for (let i = 0; i < imagePaths.length; i++) {
            try {
                const imagePath = imagePaths[i];
                console.log(`📌 Processing Image ${i + 1}/${imagePaths.length}`);

                // Wait for file input and click
                await this.page.waitForSelector('.sc-aXZVg.kGRXWn', { visible: true });
                const [fileChooser] = await Promise.all([
                    this.page.waitForFileChooser(),
                    this.page.click('.sc-aXZVg.kGRXWn')
                ]);
                await fileChooser.accept([imagePath]);

                // Wait for upload button
                await this.page.waitForSelector('button:has-text("Upload")', { visible: true });
                await this.page.click('button:has-text("Upload")');

                // Wait for upload success 
                await this.page.waitForSelector('.file-upload-success', { visible: true });
                console.log(`✓ Upload successful for image ${i + 1}`);

                // Wait between uploads
                if (i < imagePaths.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }

            } catch (error) {
                console.log(`\n❌ Error: ${error.message}`);
                const retry = await this.promptUser('🔄 Retry this upload? (y/n): ');
                if (retry.toLowerCase() === 'y') {
                    i--;
                    continue;
                }
            }
        }
    }

    async verifyWalletConnection() {
        try {
            // Try getting network info first
            const network = await this.provider.getNetwork();
            console.log('\n=== Wallet Connection Status ===');
            console.log('Network:', this.networkName);
            console.log('Chain ID:', network.chainId);

            // Then check wallet balance
            const balance = await this.wallet.getBalance();
            console.log('Address:', this.wallet.address);
            console.log('Balance:', ethers.utils.formatEther(balance), this.symbol);
            
            // Get latest block
            const block = await this.provider.getBlockNumber();
            console.log('Latest Block:', block);
            console.log('\n✓ Wallet connected successfully\n');
            
            return true;
        } catch (error) {
            console.log('\n❌ Wallet Connection Failed');
            console.log('Error:', error.message);
            return false;
        }
    }

    async run(numImages) {
        try {
            console.log('\n🚀 STORAGE SCAN AUTOMATION STARTING');
            
            // First verify wallet connection
            const isConnected = await this.verifyWalletConnection();
            if (!isConnected) {
                throw new Error('Wallet connection failed. Please check your private key and network connection.');
            }

            // Initialize browser 
            await this.initBrowser();
            
            // Connect wallet with manual confirmation
            await this.connectWallet();

            // Download and upload images
            const images = await this.downloadRandomImages(numImages);
            await this.uploadImages(images);

            console.log('\n✨ AUTOMATION COMPLETED SUCCESSFULLY');

        } catch (error) {
            console.log('\n❌ ERROR OCCURRED');
            console.log(`Details: ${error.message}`);
            throw error;

        } finally {
            if (this.browser) {
                await this.browser.close();
            }
            this.cleanupImages();
        }
    }

    async promptUser(question) {
        const readline = require('readline').createInterface({
            input: process.stdin,
            output: process.stdout
        });

        return new Promise(resolve => {
            readline.question(question, answer => {
                readline.close();
                resolve(answer);
            });
        });
    }
}

async function main() {
    console.log('\n=== Storage Scan Automation Tool ===');
    
    let numImages;
    while (true) {
        const input = await new StorageScanAutomation().promptUser('\nHow many images would you like to upload? ');
        numImages = parseInt(input);
        if (numImages > 0) break;
        console.log('Please enter a positive number.');
    }

    const automation = new StorageScanAutomation();
    await automation.run(numImages);
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = StorageScanAutomation;