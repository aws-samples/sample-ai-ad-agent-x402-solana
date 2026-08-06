"""
Utility script to generate a new Solana keypair for testing.
"""

import json
from solders.keypair import Keypair


def main():
    """Generate a new Solana keypair."""
    print("Generating new Solana keypair...\n")

    # Generate keypair
    keypair = Keypair()

    # Get public key
    public_key = str(keypair.pubkey())

    # Get private key as array
    private_key_array = list(bytes(keypair))

    print("=" * 70)
    print("NEW SOLANA KEYPAIR GENERATED")
    print("=" * 70)
    print(f"\nPublic Key (Address):")
    print(f"  {public_key}")
    print(f"\nPrivate Key (JSON Array format - for .env):")
    print(f"  {json.dumps(private_key_array)}")
    print("\n" + "=" * 70)
    print("IMPORTANT: Keep your private key secure!")
    print("=" * 70)

    # Save to file option
    save = input("\nDo you want to save this keypair to a file? (yes/no): ")
    if save.lower() in ["yes", "y"]:
        filename = input("Enter filename (default: keypair.json): ").strip()
        if not filename:
            filename = "keypair.json"

        with open(filename, "w") as f:
            json.dump(private_key_array, f)

        print(f"\n✓ Keypair saved to {filename}")
        print(f"\nTo use this keypair, add to your .env file:")
        print(f'  SOLANA_PRIVATE_KEY={json.dumps(private_key_array)}')

    # Instructions
    print("\n" + "=" * 70)
    print("NEXT STEPS (for devnet testing)")
    print("=" * 70)
    print(f"\n1. Fund your wallet with SOL (for transaction fees):")
    print(f"   solana airdrop 1 {public_key} --url devnet")
    print(f"\n2. Get devnet USDC from a faucet or another wallet")
    print(f"   USDC Devnet Mint: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
    print(f"\n3. Add to your .env file:")
    print(f'   SOLANA_PRIVATE_KEY={json.dumps(private_key_array)}')
    print(f"\n4. Run an example:")
    print(f"   python example_basic.py")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
