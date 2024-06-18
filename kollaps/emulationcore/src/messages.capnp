@0x9eb32e19f86ff170;

struct Message {
  round @0 : UInt32;
  flows @1 : List(Flow);
}

struct Link {
  id @0 : UInt16;
}

struct Flow {
  bw @0: UInt32;
  links @1: List(Link);
}