Last login: Mon Oct  6 21:16:42 on ttys001
stefanolorini@Stefanos-MBP backend % cd "/Users/stefanolorini/Desktop/endurance_hub_plus/backend"
mkdir -p app/routers
open -a "Sublime Text" app/routers/dashboard.py
The file /Users/stefanolorini/Desktop/endurance_hub_plus/backend/app/routers/dashboard.py does not exist.
stefanolorini@Stefanos-MBP backend % cd "/Users/stefanolorini/Desktop/endurance_hub_plus/backend"
stefanolorini@Stefanos-MBP backend % mkdir -p app/routers
stefanolorini@Stefanos-MBP backend % open -a "Sublime Text" app/routers/dashboard.py
The file /Users/stefanolorini/Desktop/endurance_hub_plus/backend/app/routers/dashboard.py does not exist.
stefanolorini@Stefanos-MBP backend % cd "/Users/stefanolorini/Desktop/endurance_hub_plus/backend"
stefanolorini@Stefanos-MBP backend % mkdir -p app/routers
: > app/__init__.py
: > app/routers/__init__.py
stefanolorini@Stefanos-MBP backend % open -a "Sublime Text" app/routers/dashboard_api.py || nano app/routers/dashboard_api.py
The file /Users/stefanolorini/Desktop/endurance_hub_plus/backend/app/routers/dashboard_api.py does not exist.



























































  UW PICO 5.09                                      File: app/routers/dashboard_api.py                                      Modified  

        n.raise_for_status()
        nutrition = n.json()

        # weather
        use_lat = lat if lat is not None else (met.get("home_lat") or DEFAULT_LAT)
        use_lon = lon if lon is not None else (met.get("home_lon") or DEFAULT_LON)
        w = await client.get(f"{API_BASE_URL}/weather/today", params={"lat": use_lat, "lon": use_lon}, headers=headers)
        w.raise_for_status()
        weather = w.json()
        
    notices = []
    ftp = met.get("ftp_watts")
    if ftp in (None, 0, "null"):
        notices.append("FTP missing: schedule test or enable auto-derivation.")
    
    return {
        "date": str(date.today()),  
        "readiness": {
            "hr_rest": met.get("hr_rest"),
            "hrv_ms": met.get("hrv_ms"),
            "sleep_h": met.get("sleep_hours"),
            "status": met.get("readiness_status", "unknown"),
            "notes": met.get("readiness_notes"),
        },
        "session": plan.get("session") if isinstance(plan, dict) else plan,
        "nutrition": nutrition.get("targets") if isinstance(nutrition, dict) else nutrition,
        "weather": weather,
        "notices": notices,
        "source": {
            "metrics": f"{API_BASE_URL}/metrics/latest",
            "plan": f"{API_BASE_URL}/plan/today",
            "nutrition": f"{API_BASE_URL}/nutrition/today",
            "weather": f"{API_BASE_URL}/weather/today",
        },
    }   
        
        

        
        
        
        
        
        

    
    
    
        

    
        
        
            
            
            
            
            
          
        
        
        
        
        
            
            
            
            
          

^G Get Help           ^O WriteOut           ^R Read File          ^Y Prev Pg            ^K Cut Text           ^C Cur Pos            
^X Exit               ^J Justify            ^W Where is           ^V Next Pg            ^U UnCut Text         ^T To Spell           
