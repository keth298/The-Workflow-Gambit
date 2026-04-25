# ── HyperKnight Chess Engine Makefile ─────────────────────────────────────────

CXX      := g++
TARGET   := hyperknight
SRCDIR   := src
OBJDIR   := obj

SRCS := $(wildcard $(SRCDIR)/*.cpp)
OBJS := $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(SRCS))

# ── Compiler flags ────────────────────────────────────────────────────────────
CXXFLAGS := -std=c++17 -O3 -march=native -DNDEBUG
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter
CXXFLAGS += -fno-exceptions
LDFLAGS  := -lpthread

# ── Debug build target ────────────────────────────────────────────────────────
debug: CXXFLAGS := -std=c++17 -O0 -g -DDEBUG -Wall -Wextra
debug: $(TARGET)

# ── Default release build ─────────────────────────────────────────────────────
all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(OBJDIR):
	mkdir -p $(OBJDIR)

clean:
	rm -rf $(OBJDIR) $(TARGET)

.PHONY: all clean debug
