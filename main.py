from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from abc import ABC, abstractmethod

# Inicializar la aplicación FastAPI
app = FastAPI()

# Singleton: Gestor de Disponibilidad de Habitaciones
class RoomAvailabilityManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomAvailabilityManager, cls).__new__(cls)
            cls._instance.available_rooms = {
                "standard": 10,
                "suite": 5,
                "deluxe": 3
            }
        return cls._instance

    def check_availability(self, room_type):
        return self.available_rooms.get(room_type, 0) > 0

    def book_room(self, room_type):
        if self.check_availability(room_type):
            self.available_rooms[room_type] -= 1
            return True
        return False

# Factory Method: Tipos de Habitaciones
class Room(ABC):
    @abstractmethod
    def description(self):
        pass

class StandardRoom(Room):
    def description(self):
        return "Habitación Estándar"

class SuiteRoom(Room):
    def description(self):
        return "Habitación Suite"

class DeluxeRoom(Room):
    def description(self):
        return "Habitación Deluxe"

class RoomFactory:
    @staticmethod
    def create_room(room_type):
        if room_type == "standard":
            return StandardRoom()
        elif room_type == "suite":
            return SuiteRoom()
        elif room_type == "deluxe":
            return DeluxeRoom()
        else:
            raise ValueError("Tipo de habitación no disponible.")

# Observer: Notificación de reservas
class Observer(ABC):
    @abstractmethod
    def update(self, message):
        pass

class User(Observer):
    def __init__(self, name):
        self.name = name

    def update(self, message):
        print(f"Notificación para {self.name}: {message}")

class ReservationNotifier:
    def __init__(self):
        self.observers = []

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify_all(self, message):
        for observer in self.observers:
            observer.update(message)

# Decorator: Servicios adicionales
class Reservation:
    def __init__(self, room):
        self.room = room
        self.services = []

    def cost(self):
        return 300000  # Costo base de la habitación en COP

    def description(self):
        return self.room.description() + " con " + ", ".join(self.services) if self.services else ""

class ServiceDecorator(Reservation):
    def __init__(self, reservation):
        self.reservation = reservation

    def cost(self):
        return self.reservation.cost()

    def description(self):
        return self.reservation.description()

class BreakfastDecorator(ServiceDecorator):
    def cost(self):
        return self.reservation.cost() + 50000  # Precio del desayuno en COP

    def description(self):
        return self.reservation.description() + ", desayuno incluido"

class AirportTransportDecorator(ServiceDecorator):
    def cost(self):
        return self.reservation.cost() + 70000  # Precio del transporte al aeropuerto en COP

    def description(self):
        return self.reservation.description() + ", transporte al aeropuerto"

# Strategy: Estrategias de precios
class PricingStrategy(ABC):
    @abstractmethod
    def calculate_price(self, base_price):
        pass

class HighSeasonStrategy(PricingStrategy):
    def calculate_price(self, base_price):
        return base_price * 1.5

class LowSeasonStrategy(PricingStrategy):
    def calculate_price(self, base_price):
        return base_price * 0.8

class LongStayDiscountStrategy(PricingStrategy):
    def calculate_price(self, base_price):
        return base_price * 0.9

# Sistema de Reservas de Hotel
class HotelReservationSystem:
    def __init__(self):
        self.room_manager = RoomAvailabilityManager()
        self.notifier = ReservationNotifier()

    def create_reservation(self, user, room_type, services=None, pricing_strategy=None):
        if self.room_manager.book_room(room_type):
            room = RoomFactory.create_room(room_type)
            reservation = Reservation(room)

            if services:
                for service in services:
                    if service == "breakfast":
                        reservation = BreakfastDecorator(reservation)
                    elif service == "airport_transport":
                        reservation = AirportTransportDecorator(reservation)

            if pricing_strategy:
                final_price = pricing_strategy.calculate_price(reservation.cost())
            else:
                final_price = reservation.cost()

            self.notifier.notify_all(f"Reserva confirmada para {user.name}: {reservation.description()}. Precio: {final_price:,} COP.")
            return reservation, final_price
        else:
            raise HTTPException(status_code=400, detail=f"No hay disponibilidad para el tipo de habitación: {room_type}.")

# Crear un objeto del sistema de reservas
hotel_system = HotelReservationSystem()

# Modelo de Pydantic para manejar la entrada de datos
class ReservationRequest(BaseModel):
    user_name: str
    room_type: str
    services: list[str] = []
    pricing_strategy: str = None

# Endpoints para la API

@app.post("/reservations/")
def make_reservation(request: ReservationRequest):
    # Crear usuario y agregarlo como observador
    user = User(request.user_name)
    hotel_system.notifier.add_observer(user)

    # Elegir estrategia de precios
    if request.pricing_strategy == "high_season":
        strategy = HighSeasonStrategy()
    elif request.pricing_strategy == "low_season":
        strategy = LowSeasonStrategy()
    elif request.pricing_strategy == "long_stay":
        strategy = LongStayDiscountStrategy()
    else:
        strategy = None

    # Crear reserva
    try:
        reservation, final_price = hotel_system.create_reservation(user, request.room_type, request.services, strategy)
        return {
            "message": f"Reserva confirmada para {user.name}. Descripción: {reservation.description()}",
            "final_price": final_price
        }
    except HTTPException as e:
        raise e

@app.get("/availability/{room_type}")
def check_availability(room_type: str):
    available = hotel_system.room_manager.check_availability(room_type)
    return {"room_type": room_type, "available": available}
