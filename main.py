from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import DB_helper
import generic_helper
app = FastAPI()

inprogress_orders={}
@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    intent = payload["queryResult"]["intent"]["displayName"]
    parameters = payload["queryResult"]["parameters"]
    output_contexts = payload["queryResult"]["outputContexts"]
    session_id=generic_helper.extract_session_id(output_contexts[0]["name"])

    intent_handler_dict={
        "order_add": add_to_order,
        "order_complete": complete_order,
        "order_remove": remove_from_order,
        "track_order-context-ongoing-tracking": track_order
    }
    return intent_handler_dict[intent](parameters,session_id)

def add_to_order(parameters: dict,session_id: str):
    food_items=parameters["food_item"]
    quantities=parameters["number"]

    if len(food_items)!=len(quantities):
        fulfillmentText="Sorry I didnt understand , could you please specify food items and quantities?"
    else:
        new_food_dict=dict(zip(food_items,quantities))

        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id]=new_food_dict

        order_str=generic_helper.get_items_from_food_dict(inprogress_orders[session_id])

        fulfillmentText=f"so far you have {order_str}. Do you need anything else?"

    return JSONResponse(content={
        "fulfillmentText": fulfillmentText
    })

def remove_from_order(parameters,session_id):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items=parameters["food_item"]
    curr_order=inprogress_orders[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in curr_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del curr_order[item]

    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'

    if len(curr_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_items_from_food_dict(curr_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })

def complete_order(parameters: dict,session_id: str):
    if session_id not in inprogress_orders:
        fulfillmentText="I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_orders[session_id]
        order_id=save_to_db(order)
        if order_id==-1:
            fulfillmentText="Sorry, I couldn't process your order due to a backend error. " \
                            "Please place a new order again"
        else:
            order_total = DB_helper.get_total_order_price(order_id)
            fulfillment_text = f"Awesome. We have placed your order. " \
                           f"Here is your order id # {order_id}. " \
                           f"Your order total is {order_total} which you can pay at the time of delivery!"

        del inprogress_orders[session_id]

        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

def save_to_db(order):
    order_id=DB_helper.get_next_order_id()
    for food_item,quantity in order.items():
        rcode=DB_helper.insert_order_item(food_item,quantity,order_id)

        if rcode==-1:
            return -1
    DB_helper.insert_order_tracking(order_id,"in progress")

    return order_id

def track_order(parameters,session_id):
    order_id = parameters.get("order_id")
    status = DB_helper.get_order_status(order_id)

    if status:
        fulfillmentText = f"The order status for {order_id} is: {status}"
    else:
        fulfillmentText = f"No order found for {order_id}"

    return JSONResponse(content={
        "fulfillmentText": fulfillmentText
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
