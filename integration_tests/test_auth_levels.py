import os
import time

from web3 import Web3

from deta3 import Client
from deta3 import detaApiError
from deta3 import SignableWithdrawal
from deta3 import constants
from deta3 import generate_private_key_hex_unsafe
from deta3 import private_key_to_public_key_pair_hex
from deta3.helpers.request_helpers import random_client_id

from tests.constants import DEFAULT_HOST
from tests.constants import DEFAULT_NETWORK_ID
from tests.constants import SEVEN_DAYS_S

HOST = os.environ.get('V3_API_HOST', DEFAULT_HOST)
NETWORK_ID = int(os.environ.get('NETWORK_ID', DEFAULT_NETWORK_ID))


class TestAuthLevels():

    def test_public(self):
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
        )
        client.public.get_markets()

    def test_private_with_private_keys(self):
        # Generate STARK keys and Ethhereum account.
        stark_private_key = generate_private_key_hex_unsafe()
        eth_account = Web3(None).eth.account.create()

        # Get public key.
        stark_public_key, stark_public_key_y_coordinate = (
            private_key_to_public_key_pair_hex(stark_private_key)
        )

        # Onboard the user.
        Client(
            host=HOST,
            network_id=NETWORK_ID,
            eth_private_key=eth_account.key,
        ).onboarding.create_user(
            stark_public_key=stark_public_key,
            stark_public_key_y_coordinate=stark_public_key_y_coordinate,
        )

        # Create a second client WITHOUT eth_private_key.
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
            stark_private_key=stark_private_key,
        )

        # Get the primary account.
        get_account_result = client.private.get_account(
            ethereum_address=eth_account.address,
        )
        account = get_account_result['account']

        # Initiate a regular (slow) withdrawal.
        #
        # Expect signature validation to pass, although the collateralization
        # check will fail.
        expected_error = (
            'Withdrawal would put account under collateralization minumum'
        )
        expiration_epoch_seconds = time.time() + SEVEN_DAYS_S + 60
        try:
            client.private.create_withdrawal(
                position_id=account['positionId'],
                amount='1',
                asset=constants.ASSET_USDC,
                to_address=eth_account.address,
                expiration_epoch_seconds=expiration_epoch_seconds,
            )
        except detaApiError as e:
            if expected_error not in str(e):
                raise

    def test_private_without_stark_private_key(self):
        # Generate STARK keys and Ethhereum account.
        stark_private_key = generate_private_key_hex_unsafe()
        eth_account = Web3(None).eth.account.create()

        # Get public key.
        stark_public_key, stark_public_key_y_coordinate = (
            private_key_to_public_key_pair_hex(stark_private_key)
        )

        # Onboard the user.
        Client(
            host=HOST,
            network_id=NETWORK_ID,
            eth_private_key=eth_account.key,
        ).onboarding.create_user(
            stark_public_key=stark_public_key,
            stark_public_key_y_coordinate=stark_public_key_y_coordinate,
        )

        # Create a second client WITHOUT eth_private_key or stark_private_key.
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
        )

        # Get the primary account.
        get_account_result = client.private.get_account(
            ethereum_address=eth_account.address,
        )
        account = get_account_result['account']

        # Sign a withdrawal.
        client_id = random_client_id()
        expiration_epoch_seconds = time.time() + SEVEN_DAYS_S + 60
        signable_withdrawal = SignableWithdrawal(
            network_id=NETWORK_ID,
            position_id=account['positionId'],
            client_id=client_id,
            human_amount='1',
            expiration_epoch_seconds=expiration_epoch_seconds,
        )
        signature = signable_withdrawal.sign(stark_private_key)

        # Initiate a regular (slow) withdrawal.
        #
        # Expect signature validation to pass, although the collateralization
        # check will fail.
        expected_error = (
            'Withdrawal would put account under collateralization minumum'
        )
        try:
            client.private.create_withdrawal(
                position_id=account['positionId'],
                amount='1',
                asset=constants.ASSET_USDC,
                to_address=eth_account.address,
                client_id=client_id,
                expiration_epoch_seconds=expiration_epoch_seconds,
                signature=signature,
            )
        except detaApiError as e:
            if expected_error not in str(e):
                raise

    def test_onboard_with_private_keys(self):
        # Generate keys.
        stark_private_key = generate_private_key_hex_unsafe()
        eth_private_key = Web3(None).eth.account.create().key

        # Create client WITH private keys.
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
            stark_private_key=stark_private_key,
            eth_private_key=eth_private_key,
        )

        # Onboard the user.
        client.onboarding.create_user()

        # Register and then revoke a second API key.
        client.eth_private.create_api_key()
        client.private.get_api_keys()

        # TODO
        # client.eth_private.delete_api_key(api_public_key_2)

    def test_onboard_with_web3_provider(self):
        # Generate private key.
        stark_private_key = generate_private_key_hex_unsafe()

        # Get public key.
        stark_public_key, stark_public_key_y_coordinate = (
            private_key_to_public_key_pair_hex(stark_private_key)
        )

        # Get account address from local Ethereum node.
        ethereum_address = Web3().eth.accounts[0]

        # Create client WITHOUT any private keys.
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
            web3_provider=Web3.HTTPProvider('http://localhost:8545'),
        )

        # Onboard the user.
        try:
            client.onboarding.create_user(
                ethereum_address=ethereum_address,
                stark_public_key=stark_public_key,
                stark_public_key_y_coordinate=stark_public_key_y_coordinate,
            )

        # If the Ethereum address was already onboarded, ignore the error.
        except detaApiError:
            pass

        # Register and then revoke a second API key.
        client.eth_private.create_api_key(
            ethereum_address=ethereum_address,
        )
        client.private.get_api_keys()
        client.eth_private.delete_api_key(
            api_key=client.api_key_credentials['key'],
            ethereum_address=ethereum_address,
        )

    def test_onboard_with_web3_default_account(self):
        # Generate private key.
        stark_private_key = generate_private_key_hex_unsafe()

        # Get public key.
        stark_public_key, stark_public_key_y_coordinate = (
            private_key_to_public_key_pair_hex(stark_private_key)
        )

        # Connect to local Ethereum node.
        web3 = Web3()
        web3.eth.defaultAccount = web3.eth.accounts[1]

        # Create client WITHOUT any private keys.
        client = Client(
            host=HOST,
            network_id=NETWORK_ID,
            web3=web3,
        )

        # Onboard the user.
        try:
            client.onboarding.create_user(
                stark_public_key=stark_public_key,
                stark_public_key_y_coordinate=stark_public_key_y_coordinate,
            )

        # If the Ethereum address was already onboarded, ignore the error.
        except detaApiError:
            pass

        # Register and then revoke a second API key.
        client.eth_private.create_api_key()
        client.private.get_api_keys()
        client.eth_private.delete_api_key(
            api_key=client.api_key_credentials['key'],
        )
