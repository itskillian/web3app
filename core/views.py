import re

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
# from django.urls import reverse
# from django.views import View

from .context_processors import eth_price_context, gas_price_context
from .forms import AddressForm, ConversionForm
from .models import Txn
from .utils import eth_usd_converter, get_block_num, get_eth_balance, get_eth_supply, get_node_count, get_normal_txns, wei_to_eth

def index(request):
    if request.method == 'GET':
        # load empty form
        search_form = AddressForm()

        # load home page stats
        eth_supply_dict = get_eth_supply()

        # calculate ETH total supply
        for key in eth_supply_dict:
            eth_supply_dict[key] = int(eth_supply_dict[key])
        
        eth_supply_wei = (eth_supply_dict['EthSupply']
                          + eth_supply_dict['Eth2Staking'] 
                          - eth_supply_dict['BurntFees'])
        
        eth_supply = wei_to_eth(eth_supply_wei)

        # fetch eth price data
        eth_context = eth_price_context(request)['eth_context']
        eth_usd = float(eth_context['ethusd'])

        # calculate ETH market cap
        eth_market_cap = eth_supply * eth_usd

        # fetch gas price data
        gas_context = gas_price_context(request)['gas_context']

        # fetch block number
        block_num = get_block_num()

        node_count = get_node_count()['TotalNodeCount']

        # session visit counter
        num_visits = request.session.get('num_visits', 0)
        request.session['num_visits'] = num_visits + 1
        
        context = {
            'search_form': search_form,
            'eth_context': eth_context,
            'gas_context': gas_context,
            'eth_supply': eth_supply,
            'eth_market_cap': eth_market_cap,
            'block_num': block_num,
            'node_count': node_count,
            'num_visits': num_visits,
            }
        
        return render(request, 'core/index.html', context)


def search(request):
    if request.method == 'POST':
        # form validation
        search_form = AddressForm(request.POST)
        if search_form.is_valid():
            address = search_form.cleaned_data['address']
            
            # check address format validity
            if len(address) != 42:
                raise ValidationError(f'Invalid address length {len(address)}. Must be 42 characters')
            if not address.startswith('0x'):
                raise ValidationError("Invalid address format. Must start with '0x'.")
            if not re.match(r'^0x[0-9a-fA-F]{40}$', address):
                raise ValidationError('Invalid address format. Must contain only hexadecimal characters')
                # redirect to address view, passing address as arg
            
            # redirect valid address to address view
            return redirect('core:address', address=address)
        
        # redirect invalid address to error view
        return redirect('core:error')


def address(request, address):
    # fetch balance data
    try:
        eth_balance = wei_to_eth(get_eth_balance(address))
    except ValueError:
        print('value error, address not valid')
        return redirect('core:error')
    
    # fetch eth price data
    eth_usd = eth_price_context(request)['eth_context']['ethusd']
    eth_value = eth_balance * float(eth_usd)
    
    # fetch transaction data
    txn_data = get_normal_txns(address)

    for data in txn_data:
        t, created = Txn.objects.get_or_create(
            transaction_hash = data['hash'],
            defaults={
                'block_number' : data['blockNumber'],
                'timestamp' : data['timeStamp'],
                'nonce' : data['nonce'],
                'block_hash' : data['blockHash'],
                'transaction_index' : data['transactionIndex'],
                'from_address' : data['from'],
                'to_address' : data['to'],
                'value' : data['value'],
                'gas' : data['gas'],
                'gas_price' : data['gasPrice'],
                'is_error' : data['isError'],
                'txreceipt_status' : data['txreceipt_status'],
                'input' : data['input'],
                'contract_address' : data['contractAddress'],
                'cumulative_gas_used' : data['cumulativeGasUsed'],
                'gas_used' : data['gasUsed'],
                'confirmations' : data['confirmations'],
                'method_id' : data['methodId'],
                'function_name' : data['functionName'],
            }
        )
        if not created:
            print('duplicate entry found, skipping')

    # convert wallet balance from wei to eth
    # TODO make this into a custom template filter
    for txn in txn_data:
        txn['value'] = wei_to_eth(txn['value'])
    
    # session add address to search history
    if 'search_history' not in request.session:
        request.session['search_history'] = []

    search_history = request.session['search_history']
    if address not in search_history:
        search_history.append(address)
        if len(search_history) > 10:
            search_history.pop(0)
    
    request.session['search_history'] = search_history

    context = {
        'eth_balance': eth_balance,
        'eth_value': eth_value,
        'address': address,
        'txn_data': txn_data,
    }
    return render(request, 'core/address.html', context)


def conversion(request):
    if request.method == 'GET':
        conversion_form = ConversionForm()
        return render(request, 'core/conversion.html', {'conversion_form': conversion_form})
    elif request.method == 'POST':
        conversion_form = ConversionForm(request.POST)
        if conversion_form.is_valid():
            amount = conversion_form.cleaned_data['amount']
            from_currency = conversion_form.cleaned_data['from_currency']
            to_currency = conversion_form.cleaned_data['to_currency']
            converted_amount = eth_usd_converter(amount, from_currency, to_currency)
            return JsonResponse({'converted_amount': converted_amount})
        else:
            return JsonResponse({'error': 'Invalid form'}, status=400)


def error(request):
    error = 'An error has occured'
    return render(request, 'core/error.html', {'error': error})