# Glamsterdam deployment gas dimensions

Across all 35 deployment transactions, receipt gas was **610,627,957**: **600,774,390 state gas (98.39%)** and **9,853,567 execution gas (1.61%)**.

All 16 transactions whose receipt gas exceeded the EIP-7825 16,777,216 execution-gas cap did so because of state gas. Their execution portions remained below the cap.

## Transactions over 16,777,216 total gas

| Phase | Description | Transaction | Receipt gas | State gas | Execution gas | State share |
|---|---|---|---:|---:|---:|---:|
| deploy-implementations-01 | Deploy the SystemConfig implementation | `0xf1636333db6a76f392676ab2b87661cd3d0356c41cde78c9c6b5cf4950e14100` | 20,032,541 | 19,779,840 | 252,701 | 98.74% |
| deploy-implementations-04 | Deploy the L1StandardBridge implementation | `0x0ddaf1e3a9ddf1fcd713f4c16fb367a5a9973e08eb2ab7ffcf5bcf0a37557e8e` | 19,823,841 | 19,590,120 | 233,721 | 98.82% |
| deploy-implementations-05 | Deploy the OptimismMintableERC20Factory implementation | `0x2b8a869a94ef532e5c4535c6a1cdd22d64065a4f16e215ce051dce369f31442e` | 18,714,403 | 18,496,170 | 218,233 | 98.83% |
| deploy-implementations-06 | Deploy the OptimismPortal2 implementation | `0x45a060b2ff59e437c0c820710940d3621a791ad7e372deff017922e63d1ea412` | 35,078,032 | 34,697,340 | 380,692 | 98.91% |
| deploy-implementations-09 | Deploy the PreimageOracle singleton | `0xe75edd8b022f21ff43eb07e2e6b41b4454804f83db50526b42afb5b13041c18a` | 23,920,164 | 23,470,200 | 449,964 | 98.12% |
| deploy-implementations-10 | Deploy the MIPS64 singleton | `0xce6b9ef3062e151c2c8d4b0158ff0e3ff63c8a9a4b3377338624672496e7200c` | 33,406,276 | 33,028,110 | 378,166 | 98.87% |
| deploy-implementations-13 | Deploy the FaultDisputeGame implementation | `0x9fba7b23a237febd8ae85f99e5b2fc354b239d4ebfeb609fb2c02b6ee6509aad` | 37,024,856 | 36,625,140 | 399,716 | 98.92% |
| deploy-implementations-14 | Deploy the PermissionedDisputeGame implementation | `0xdc2dc491492c3af9a6a7dd3bfc85c549fd74ebb29ba245a6a548ad7da5d59a89` | 37,766,433 | 37,359,540 | 406,893 | 98.92% |
| deploy-implementations-15 | Deploy the SuperFaultDisputeGame implementation | `0x21bc1cf4a33502054c946233154270b79884f9247ed4b6ffe8677b2733a96f00` | 33,909,847 | 33,540,660 | 369,187 | 98.91% |
| deploy-implementations-24 | Deploy StandardValidatorUtils | `0x8a42d8327783fa5d9bd7f6ebe4de5028b1ca38f2890fbae41d9f11f8eb97e7fa` | 28,428,191 | 28,118,340 | 309,851 | 98.91% |
| deploy-implementations-25 | Deploy OPContractsManagerMigrationValidator | `0xb7b735e4e7f8bb21117db32b842ef1895896d906435dba6cf47c4843ddc88a3c` | 26,784,992 | 26,491,950 | 293,042 | 98.91% |
| deploy-implementations-26 | Deploy OPContractsManagerStandardValidator | `0xf50e43617ca6468a393207402f4754bbb6bd30696c5ef96b965dce2be41a5aa8` | 33,739,558 | 33,083,190 | 656,368 | 98.05% |
| deploy-implementations-27 | Deploy OPContractsManagerUtils | `0xc708a86dead0f9f5e27de2e6ab432caaf5f6e3328d78d06e85342572b1b722c7` | 23,083,766 | 22,826,070 | 257,696 | 98.88% |
| deploy-implementations-28 | Deploy OPContractsManagerMigrator | `0xdfae32f26502d825cbaddf5ea6f1c5850ee5cc82cf2259178d95e9c507743341` | 22,323,943 | 22,073,310 | 250,633 | 98.88% |
| deploy-implementations-29 | Deploy OPContractsManagerV2 | `0x6603ebee84d0c23576d38402453e15d80077e5aa4409a3394e10b77188607645` | 37,530,935 | 37,123,920 | 407,015 | 98.92% |
| deploy-op-chain | Deploy and initialize the chain-specific L1 contracts through OPContractsManagerV2 | `0x112e5369299950cf31b03b105c613af74d35cf68bfb82a9fdc693cf856a2f639` | 54,771,292 | 52,353,540 | 2,417,752 | 95.59% |

## All deployment transactions

| Phase | Description | Nonce | Receipt gas | State gas | Execution gas | New accounts | Code bytes | New slots | Block gas | Bottleneck |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| deploy-superchain-01 | Deploy the Superchain ProxyAdmin | 0 | 10,404,725 | 10,263,240 | 141,485 | 1 | 6,524 | 1 | 10,263,240 | state |
| deploy-superchain-02 | Deploy the SuperchainConfig implementation | 1 | 5,166,384 | 5,073,480 | 92,904 | 1 | 3,132 | 1 | 5,073,480 | state |
| deploy-superchain-03 | Deploy the SuperchainConfig proxy | 2 | 3,506,360 | 3,431,790 | 74,570 | 1 | 2,059 | 1 | 3,431,790 | state |
| deploy-superchain-04 | Upgrade and initialize the SuperchainConfig proxy | 3 | 258,166 | 195,840 | 62,326 | 0 | 0 | 2 | 195,840 | state |
| deploy-superchain-05 | Transfer ownership of the Superchain ProxyAdmin | 4 | 19,762 | 0 | 19,762 | 0 | 0 | 0 | 19,762 | execution |
| deploy-implementations-01 | Deploy the SystemConfig implementation | 5 | 20,032,541 | 19,779,840 | 252,701 | 1 | 12,680 | 2 | 19,779,840 | state |
| deploy-implementations-02 | Deploy the L1CrossDomainMessenger implementation | 6 | 15,180,027 | 14,990,940 | 189,087 | 1 | 9,614 | 1 | 14,990,940 | state |
| deploy-implementations-03 | Deploy the L1ERC721Bridge implementation | 7 | 9,884,114 | 9,746,100 | 138,014 | 1 | 6,186 | 1 | 9,746,100 | state |
| deploy-implementations-04 | Deploy the L1StandardBridge implementation | 8 | 19,823,841 | 19,590,120 | 233,721 | 1 | 12,620 | 1 | 19,590,120 | state |
| deploy-implementations-05 | Deploy the OptimismMintableERC20Factory implementation | 9 | 18,714,403 | 18,496,170 | 218,233 | 1 | 11,905 | 1 | 18,496,170 | state |
| deploy-implementations-06 | Deploy the OptimismPortal2 implementation | 10 | 35,078,032 | 34,697,340 | 380,692 | 1 | 22,494 | 1 | 34,697,340 | state |
| deploy-implementations-07 | Deploy the ETHLockbox implementation | 11 | 7,927,705 | 7,807,590 | 120,115 | 1 | 4,919 | 1 | 7,807,590 | state |
| deploy-implementations-08 | Deploy the DelayedWETH implementation | 12 | 9,477,365 | 9,340,650 | 136,715 | 1 | 5,921 | 1 | 9,340,650 | state |
| deploy-implementations-09 | Deploy the PreimageOracle singleton | 13 | 23,920,164 | 23,470,200 | 449,964 | 1 | 14,260 | 15 | 23,470,200 | state |
| deploy-implementations-10 | Deploy the MIPS64 singleton | 14 | 33,406,276 | 33,028,110 | 378,166 | 1 | 21,467 | 0 | 33,028,110 | state |
| deploy-implementations-11 | Deploy the DisputeGameFactory implementation | 15 | 12,740,433 | 12,570,480 | 169,953 | 1 | 8,032 | 1 | 12,570,480 | state |
| deploy-implementations-12 | Deploy the AnchorStateRegistry implementation | 16 | 11,629,200 | 11,468,880 | 160,320 | 1 | 7,312 | 1 | 11,468,880 | state |
| deploy-implementations-13 | Deploy the FaultDisputeGame implementation | 17 | 37,024,856 | 36,625,140 | 399,716 | 1 | 23,818 | 0 | 36,625,140 | state |
| deploy-implementations-14 | Deploy the PermissionedDisputeGame implementation | 18 | 37,766,433 | 37,359,540 | 406,893 | 1 | 24,298 | 0 | 37,359,540 | state |
| deploy-implementations-15 | Deploy the SuperFaultDisputeGame implementation | 19 | 33,909,847 | 33,540,660 | 369,187 | 1 | 21,802 | 0 | 33,540,660 | state |
| deploy-implementations-16 | Deploy the SuperPermissionedDisputeGame implementation | 20 | 7,186,224 | 7,093,080 | 93,144 | 1 | 4,516 | 0 | 7,093,080 | state |
| deploy-implementations-17 | Deploy the StorageSetter upgrade helper | 21 | 1,958,010 | 1,912,500 | 45,510 | 1 | 1,130 | 0 | 1,912,500 | state |
| deploy-implementations-18 | Deploy the ERC-5202 AddressManager blueprint | 22 | 2,757,995 | 2,705,040 | 52,955 | 1 | 1,648 | 0 | 2,705,040 | state |
| deploy-implementations-19 | Deploy the ERC-5202 Proxy blueprint | 23 | 3,825,833 | 3,760,740 | 65,093 | 1 | 2,338 | 0 | 3,760,740 | state |
| deploy-implementations-20 | Deploy the ERC-5202 ProxyAdmin blueprint | 24 | 10,648,983 | 10,517,220 | 131,763 | 1 | 6,754 | 0 | 10,517,220 | state |
| deploy-implementations-21 | Deploy the ERC-5202 L1ChugSplashProxy blueprint | 25 | 4,277,407 | 4,209,030 | 68,377 | 1 | 2,631 | 0 | 4,209,030 | state |
| deploy-implementations-22 | Deploy the ERC-5202 ResolvedDelegateProxy blueprint | 26 | 2,565,407 | 2,513,790 | 51,617 | 1 | 1,523 | 0 | 2,513,790 | state |
| deploy-implementations-23 | Deploy the OPContractsManagerContainer release catalog | 27 | 4,874,787 | 4,516,560 | 358,227 | 1 | 1,424 | 22 | 4,516,560 | state |
| deploy-implementations-24 | Deploy StandardValidatorUtils | 28 | 28,428,191 | 28,118,340 | 309,851 | 1 | 18,258 | 0 | 28,118,340 | state |
| deploy-implementations-25 | Deploy OPContractsManagerMigrationValidator | 29 | 26,784,992 | 26,491,950 | 293,042 | 1 | 17,195 | 0 | 26,491,950 | state |
| deploy-implementations-26 | Deploy OPContractsManagerStandardValidator | 30 | 33,739,558 | 33,083,190 | 656,368 | 1 | 20,159 | 21 | 33,083,190 | state |
| deploy-implementations-27 | Deploy OPContractsManagerUtils | 31 | 23,083,766 | 22,826,070 | 257,696 | 1 | 14,799 | 0 | 22,826,070 | state |
| deploy-implementations-28 | Deploy OPContractsManagerMigrator | 32 | 22,323,943 | 22,073,310 | 250,633 | 1 | 14,307 | 0 | 22,073,310 | state |
| deploy-implementations-29 | Deploy OPContractsManagerV2 | 33 | 37,530,935 | 37,123,920 | 407,015 | 1 | 24,144 | 0 | 37,123,920 | state |
| deploy-op-chain | Deploy and initialize the chain-specific L1 contracts through OPContractsManagerV2 | 34 | 54,771,292 | 52,353,540 | 2,417,752 | 12 | 27,786 | 78 | 52,353,540 | state |

## Method

The exact devnet-8 constants are `CPSB=1530`, 120 bytes per new account, and 64 bytes per new storage slot. Deployed runtime code is charged one state byte per code byte. The script obtains durable pre/post state with Geth's `prestateTracer` in diff mode.

`executionGasUsedAfterRefund = receiptGasUsed - stateGasUsed`. This is the fee-bearing execution portion after ordinary execution-gas refunds. State gas is net of EIP-8037 state refills.

Every deployment block contained one transaction. For every row, `blockGasUsed == max(stateGasUsed, executionGasUsedAfterRefund)`, independently validating the split against Amsterdam's multidimensional block accounting. All but one deployment were state-gas bottlenecked.
