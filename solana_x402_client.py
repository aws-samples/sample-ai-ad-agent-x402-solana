"""
Solana x402 Payment Client

This module provides a client for making HTTP requests with x402 payment support
using Solana wallets on devnet/mainnet.
"""

import base64
import json
import time
import secrets
from typing import Optional, Callable, Dict, Any, List
import requests
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.message import Message
from solders.hash import Hash
from solana.rpc.api import Client as SolanaClient
from solana.rpc.commitment import Confirmed
from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
    transfer_checked,
    TransferCheckedParams,
)
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from strands import Agent, tool

class InsufficientBalanceError(Exception):
    """Raised when wallet has insufficient balance for payment."""
    pass

class PaymentRequirements:
    """Represents payment requirements from x402 server."""

    def __init__(self, data: Dict[str, Any]):
        self.scheme = data.get("scheme")
        self.network = data.get("network")
        self.pay_to = data.get("payTo")
        self.max_amount_required = data.get("maxAmountRequired")
        self.asset = data.get("asset")
        self.max_timeout_seconds = data.get("maxTimeoutSeconds", 3600)
        self.description = data.get("description", "")
        self.extra = data.get("extra", {})
        self.raw_data = data

    def to_dict(self) -> Dict[str, Any]:
        return self.raw_data


class SolanaX402Client:
    """Client for handling x402 payments on Solana."""

    def __init__(
        self,
        keypair: Keypair,
        rpc_url: str = "https://api.devnet.solana.com",
        max_value: Optional[int] = None,
        payment_requirements_selector: Optional[Callable] = None,
    ):
        """
        Initialize Solana x402 client.

        Args:
            keypair: Solana keypair for signing transactions
            rpc_url: Solana RPC endpoint URL
            max_value: Optional maximum allowed payment amount in base units
            payment_requirements_selector: Optional custom selector for payment requirements
        """
        self.keypair = keypair
        self.rpc_url = rpc_url
        self.solana_client = SolanaClient(rpc_url)
        self.max_value = max_value
        self._payment_requirements_selector = (
            payment_requirements_selector or self.default_payment_requirements_selector
        )

    @property
    def public_key(self) -> Pubkey:
        """Get the public key of the keypair."""
        return self.keypair.pubkey()

    @staticmethod
    def default_payment_requirements_selector(
        accepts: List[PaymentRequirements],
        network_filter: Optional[str] = None,
        scheme_filter: Optional[str] = None,
        max_value: Optional[int] = None,
    ) -> PaymentRequirements:
        """
        Select payment requirements from the list of accepted requirements.

        Args:
            accepts: List of accepted payment requirements
            network_filter: Optional network to filter by
            scheme_filter: Optional scheme to filter by
            max_value: Optional maximum allowed payment amount

        Returns:
            Selected payment requirements

        Raises:
            ValueError: If no supported scheme is found
        """
        for payment_req in accepts:
            scheme = payment_req.scheme
            network = payment_req.network

            # Check scheme filter
            if scheme_filter and scheme != scheme_filter:
                continue

            # Check network filter
            if network_filter and network != network_filter:
                continue

            if scheme == "exact":
                # Check max value if set
                if max_value is not None:
                    max_amount = int(payment_req.max_amount_required)
                    if max_amount > max_value:
                        raise ValueError(
                            f"Payment amount {max_amount} exceeds maximum allowed value {max_value}"
                        )

                return payment_req

        raise ValueError("No supported payment scheme found")

    def select_payment_requirements(
        self,
        accepts: List[PaymentRequirements],
        network_filter: Optional[str] = None,
        scheme_filter: Optional[str] = None,
    ) -> PaymentRequirements:
        """
        Select payment requirements using the configured selector.

        Args:
            accepts: List of accepted payment requirements
            network_filter: Optional network to filter by
            scheme_filter: Optional scheme to filter by

        Returns:
            Selected payment requirements
        """
        return self._payment_requirements_selector(
            accepts, network_filter, scheme_filter, self.max_value
        )

    def create_spl_token_transfer_transaction(
        self, payment_requirements: PaymentRequirements
    ) -> str:
        """
        Create and sign an SPL token transfer transaction with compute budget instructions.
        """
        try:
            # print(f"DEBUG: Payment Requirements:")
            # print(f"  - payTo: {payment_requirements.pay_to}")
            # print(f"  - asset: {payment_requirements.asset}")
            # print(f"  - amount: {payment_requirements.max_amount_required}")
    
            # Parse addresses
            pay_to_clean = str(payment_requirements.pay_to).strip()
            asset_clean = str(payment_requirements.asset).strip()
    
            mint_address = Pubkey.from_string(asset_clean)
            recipient_address = Pubkey.from_string(pay_to_clean)
            sender_pubkey = self.public_key
    
            # Determine fee payer
            if payment_requirements.extra and 'feePayer' in payment_requirements.extra:
                fee_payer_pubkey = Pubkey.from_string(payment_requirements.extra['feePayer'])
                # print(f"DEBUG: Using server fee payer: {fee_payer_pubkey}")
            else:
                fee_payer_pubkey = sender_pubkey
                # print(f"DEBUG: Using client as fee payer: {sender_pubkey}")
    
            # Get associated token accounts
            sender_token_account = get_associated_token_address(
                sender_pubkey, mint_address
            )
            recipient_token_account = get_associated_token_address(
                recipient_address, mint_address
            )
    
            # print(f"DEBUG: Token accounts:")
            # print(f"  - Sender ATA: {sender_token_account}")
            # print(f"  - Recipient ATA: {recipient_token_account}")
    
            # Get recent blockhash
            recent_blockhash_resp = self.solana_client.get_latest_blockhash(Confirmed)
            recent_blockhash = recent_blockhash_resp.value.blockhash
    
            # Build instructions list
            instructions = []
    
            # 1. ADD COMPUTE UNIT LIMIT (required by x402)
            compute_units = 200000  # Lower since no ATA creation
            compute_limit_ix = set_compute_unit_limit(compute_units)
            instructions.append(compute_limit_ix)
    
            # 2. ADD COMPUTE UNIT PRICE (required by x402)
            compute_price_ix = set_compute_unit_price(1)
            instructions.append(compute_price_ix)
    
            # 3. SKIP ATA CREATION - Assume it exists
            # (The recipient ATA should be created beforehand)
            # print("DEBUG: Skipping ATA creation (assuming it exists)")
    
            # 4. ADD TRANSFER INSTRUCTION
            decimals = 6
            transfer_ix = transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=sender_token_account,
                    mint=mint_address,
                    dest=recipient_token_account,
                    owner=sender_pubkey,
                    amount=int(payment_requirements.max_amount_required),
                    decimals=decimals,
                )
            )
            instructions.append(transfer_ix)
    
            # print(f"DEBUG: Total instructions: {len(instructions)} (expected: 3 or 4)")
            # print(f"  [0] Compute Unit Limit")
            # print(f"  [1] Compute Unit Price")
            # print(f"  [2] Transfer")
    
            # Create message with fee payer
            message = Message.new_with_blockhash(
                instructions,
                fee_payer_pubkey,
                recent_blockhash
            )
    
            # Create and sign transaction
            transaction = Transaction.new_unsigned(message)
    
            # Sign based on whether we have server fee payer
            if fee_payer_pubkey != sender_pubkey:
                # Partial sign - server will add their signature
                print("DEBUG: Partially signing (token owner only)")
                transaction.partial_sign([self.keypair], recent_blockhash)
            else:
                # Full sign - we're both fee payer and token owner
                print("DEBUG: Fully signing")
                transaction.sign([self.keypair], recent_blockhash)
    
            # print(f"DEBUG: Transaction signed")
            # print(f"DEBUG: Number of signatures: {len(transaction.signatures)}")
    
            # Serialize and encode
            serialized = bytes(transaction)
            encoded = base64.b64encode(serialized).decode("utf-8")
    
            # print(f"DEBUG: Transaction size: {len(serialized)} bytes")
    
            return encoded
    
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to create SPL token transfer: {str(e)}")
    
    def debug_transaction_detailed(self, encoded_tx: str):
        """Detailed debug of transaction structure."""
        try:
            import base64
            from solders.transaction import Transaction as SoldersTransaction
    
            decoded = base64.b64decode(encoded_tx)
            print(f"\n{'='*60}")
            print(f"TRANSACTION DEBUG")
            print(f"{'='*60}")
            print(f"Total bytes: {len(decoded)}")
            print(f"First 20 bytes (hex): {decoded[:20].hex()}")
    
            # Try to deserialize
            try:
                tx = SoldersTransaction.from_bytes(decoded)
                print(f"\nDeserialized transaction:")
                print(f"  - Number of signatures: {len(tx.signatures)}")
                print(f"  - Message accounts: {len(tx.message.account_keys)}")
                print(f"  - Instructions: {len(tx.message.instructions)}")
    
                print(f"\n  Account keys:")
                for i, key in enumerate(tx.message.account_keys):
                    print(f"    [{i}] {key}")
    
                print(f"\n  Instructions:")
                for i, ix in enumerate(tx.message.instructions):
                    print(f"    [{i}] Program index: {ix.program_id_index}, Accounts: {len(ix.accounts)}, Data length: {len(ix.data)}")
    
                print(f"\n  Signatures:")
                for i, sig in enumerate(tx.signatures):
                    print(f"    [{i}] {sig}")
    
            except Exception as e:
                print(f"Could not deserialize: {e}")
    
            print(f"{'='*60}\n")
    
        except Exception as e:
            print(f"DEBUG: Could not analyze transaction: {e}")

    def create_payment_header(
        self, payment_requirements: PaymentRequirements, x402_version: int = 1
    ) -> str:
        """
        Create a payment header for Solana.
    
        Args:
            payment_requirements: Selected payment requirements
            x402_version: x402 protocol version
    
        Returns:
            Base64 encoded payment header
        """
        try:
            # Create the signed transaction
            signed_transaction = self.create_spl_token_transfer_transaction(
                payment_requirements
            )
    
            # Debug the transaction
            # self.debug_transaction_detailed(signed_transaction)
    
            # Create payment payload
            payment_payload = {
                "scheme": payment_requirements.scheme,
                "network": payment_requirements.network,
                "x402Version": x402_version,
                "payload": {"transaction": signed_transaction},
            }
    
            # Encode to base64
            payload_json = json.dumps(payment_payload, separators=(",", ":"))
            encoded = base64.b64encode(payload_json.encode("utf-8")).decode("utf-8")
    
            return encoded
    
        except Exception as e:
            raise Exception(f"Failed to create payment header: {str(e)}")

    def check_token_balance(self, token_mint: Pubkey) -> int:
        """
        Check token balance for the client's wallet.
    
        Args:
            token_mint: The token mint address to check
    
        Returns:
            Balance in atomic units (smallest denomination)
        """
        try:
            # Get associated token account
            token_account = get_associated_token_address(
                self.public_key, token_mint
            )
    
            # Get account balance
            response = self.solana_client.get_token_account_balance(token_account)
    
            if response.value:
                return int(response.value.amount)
            return 0
    
        except Exception as e:
            print(f"   Error checking balance: {e}")
            raise

    @tool
    def make_request_(
        self,
        url: str,
        json_data: Dict[str, Any],
        method: str = "GET",
        # headers: Optional[Dict[str, str]] = None,
        # data: Optional[Any] = None,

    ) -> str:
        """
        Make a standard HTTP request without payment handling.
    
        This is a basic HTTP request wrapper that does not handle x402 payment 
        protocol. Use make_request_with_payment() for payment-gated endpoints.
    
        Args:
            url: The target URL for the HTTP request
            method: HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
                    Defaults to 'GET'
            json_data: dictionary (Python dict/object) to send as JSON in the request body.  This should be the request payload for the endpoint.
                   **IMPORTANT**: Must be a dict/object, NOT a JSON string.
                   The function will automatically serialize it to JSON.

                   ✓ CORRECT: json_data={"city": "Miami", "units": "imperial"}
                   ✗ WRONG:   json_data='{"city": "Miami", "units": "imperial"}'
                    If provided, Content-Type will be set to application/json
    
        Returns:
            str: The body of the response
    
        Example:
            >>> response = client.make_request_(
            ...     url="https://api.example.com/data",
            ...     method="GET",
            ...     json_data={
                                "query": [
                                        "sunset over mountains",
                                        "city at night",
                                        "forest in autumn"
                                      ]
                            }
            ... )
        """
        # Initial request
    
        response = requests.request(
            method=method,
            url=url,
            headers=None,
            data=None,
            json=json_data,
            allow_redirects=False,
        )

        if response.headers.get("content-type", "").startswith("application/json"):
            response_data = response.json()
        else:
            response_data = response.text

        return response_data

    @tool
    def make_request_with_payment(
        self,
        url: str,
        json_data: Dict[str, Any],
        method: str = "GET",
        # headers: Optional[Dict[str, str]] = None,
        # data: Optional[Any] = None,
        # network_filter: Optional[str] = None,
    ) -> str:
        """
        Make an HTTP request with automatic x402 payment protocol handling.
    
        This method handles the complete x402 payment flow:
        1. Makes an initial request to the endpoint
        2. If a 402 Payment Required response is received, parses payment requirements
        3. Creates and signs a payment transaction
        4. Retries the request with the payment proof in the X-Payment header
    
        The payment is automatically executed using the Solana blockchain with the
        wallet configured during client initialization.
    
        Args:
            url: The target URL for the HTTP request (payment-gated endpoint)
            method: HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
                    Defaults to 'GET'
            json_data: dictionary (Python dict/object) to send as JSON in the request body.  This should be the request payload for the endpoint.
                   **IMPORTANT**: Must be a dict/object, NOT a JSON string.
                   The function will automatically serialize it to JSON.

                   ✓ CORRECT: json_data={"city": "Miami", "units": "imperial"}
                   ✗ WRONG:   json_data='{"city": "Miami", "units": "imperial"}'
                    If provided, Content-Type will be set to application/json
    
        Returns:
            requests.Response: The body response from the endpoint  and transaction details of the payment
    
        Raises:
            InsufficientBalanceError: If the wallet does not have enough tokens to
                                     cover the required payment amount
            Exception: If the 402 response cannot be parsed, no payment requirements
                      are provided, payment creation fails, or the payment transaction
                      fails to execute
    
        Example:
            >>> # Request a paid endpoint
            >>> response = client.make_request_with_payment(
            ...     url="http://localhost:4030/image_generator",
            ...     method="POST",
            ...     json_data={"query": "sunset over mountains"}
            ... )
    
        Notes:
            - The method performs a balance check before attempting payment
            - Payment transactions are submitted to the Solana blockchain
            - If no payment is required (status code != 402), returns the initial response
        """
        
        headers = None
        data = None
        network_filter = "solana-devnet"
        # Initial request
        request_headers = headers.copy() if headers else {}
    
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            data=data,
            json=json_data,
            allow_redirects=False,
        )
    
        # Check if payment is required
        if response.status_code != 402:
            return response
    
        # Parse payment requirements
        try:
            response_data = response.json()
            # print(f"DEBUG: Full 402 response:")
            # print(json.dumps(response_data, indent=2))
    
            accepts_data = response_data.get("accepts", [])
            accepts = [PaymentRequirements(req) for req in accepts_data]
        except Exception as e:
            raise Exception(f"Failed to parse 402 response: {str(e)}")
    
        if not accepts:
            raise Exception("No payment requirements in 402 response")
    
        # Select payment requirements
        payment_requirements = self.select_payment_requirements(
            accepts, network_filter=network_filter
        )
    
        # print(f"Payment required: {payment_requirements.max_amount_required} of asset {payment_requirements.asset}")
        # print(f"Network: {payment_requirements.network}")
        # print(f"Pay to: {payment_requirements.pay_to}")
        # print(f"Description: {payment_requirements.description}")

         # ===== ADD THIS BALANCE CHECK =====
        try:
            mint_address = Pubkey.from_string(payment_requirements.asset)
            balance = self.check_token_balance(mint_address)
            required = int(payment_requirements.max_amount_required)
    
            # Get decimals for display
            decimals = 6  # Assuming 6 decimals
            balance_display = balance / (10 ** decimals)
            required_display = required / (10 ** decimals)
    
            # print(f"\n💰 Balance check:")
            # print(f"   Required: {required_display} tokens ({required} atomic units)")
            # print(f"   Available: {balance_display} tokens ({balance} atomic units)")
    
            if balance < required:
                raise InsufficientBalanceError(
                    f"Insufficient balance: need {required_display} tokens, have {balance_display} tokens"
                )
    
            # print(f"   ✓ Sufficient balance")
    
        except InsufficientBalanceError:
            raise
        except Exception as e:
            print(f"   ⚠ Warning: Could not check balance: {e}")
            print(f"   Continuing anyway...")
        # ===== END BALANCE CHECK =====
    
        # Create payment header
        payment_header = self.create_payment_header(payment_requirements)
    
        # Retry request with payment
        request_headers["X-Payment"] = payment_header
    
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            data=data,
            json=json_data,
        )

        response_att = ""
        if "x-payment-response" in response.headers or "X-Payment-Response" in response.headers:
            payment_response_header = response.headers.get("x-payment-response") or response.headers.get("X-Payment-Response")
            payment_response = decode_x_payment_response(payment_response_header)
            # print(f"\n✓ Payment successful!")
            # print(f"  Transaction: {payment_response.get('transaction')}")
            # print(f"  Network: {payment_response.get('network')}")
            # print(f"  Payer: {payment_response.get('payer')}")
            response_att += f"Transaction: {payment_response.get('transaction')}\nNetwork: {payment_response.get('network')}\nPayer: {payment_response.get('payer')}"

        if response.headers.get("content-type", "").startswith("application/json"):
            response_data = response.json()
        else:
            response_data = response.text

        response = f"{response_att}\n\n{response_data}"    
        return response


def decode_x_payment_response(header: str) -> Dict[str, Any]:
    """
    Decode the X-PAYMENT-RESPONSE header.

    Args:
        header: The X-PAYMENT-RESPONSE header to decode

    Returns:
        The decoded payment response containing transaction info
    """
    decoded = base64.b64decode(header)
    result = json.loads(decoded)
    return result


def load_keypair_from_file(filepath: str) -> Keypair:
    """
    Load a Solana keypair from a JSON file.

    Args:
        filepath: Path to the keypair JSON file

    Returns:
        Keypair object
    """
    with open(filepath, "r") as f:
        secret_key = json.load(f)
    return Keypair.from_bytes(bytes(secret_key))


def load_keypair_from_base58(private_key_base58: str) -> Keypair:
    """
    Load a Solana keypair from a base58 encoded private key.

    Args:
        private_key_base58: Base58 encoded private key

    Returns:
        Keypair object
    """
    import base58
    secret_key_bytes = base58.b58decode(private_key_base58)
    return Keypair.from_bytes(secret_key_bytes)


def load_keypair_from_env(env_var: str = "SOLANA_PRIVATE_KEY") -> Keypair:
    """
    Load a Solana keypair from an environment variable.

    Args:
        env_var: Name of the environment variable containing the private key

    Returns:
        Keypair object
    """
    import os
    private_key = os.getenv(env_var)
    if not private_key:
        raise ValueError(f"Environment variable {env_var} not found")

    # Try to parse as JSON array first
    try:
        secret_key = json.loads(private_key)
        return Keypair.from_bytes(bytes(secret_key))
    except (json.JSONDecodeError, ValueError):
        # Try base58 format
        return load_keypair_from_base58(private_key)
