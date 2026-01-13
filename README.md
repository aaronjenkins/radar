1. Get a FlightRadar API Key ($9/month for the lowest tier) https://fr24api.flightradar24.com/subscriptions-and-credits
2. Get your mesh device connected to the same wifi as the server going to host this app, and get the device IP
3. Create a dedicated channel on your mesh device to send messages, and note the channel number
4. Get your Latitudate and Longitude (note: U.S. Longitudes start with a - sign)
5. Set your .env variables
   - FR24_API_TOKEN 
   - MESH_IP
   - MESH_CHANNEL_INDEX   
