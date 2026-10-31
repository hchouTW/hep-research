// Minimal JSON reader for layered_sim specs (objects, arrays, strings, numbers, true, false, null).
// Written for this program so that no third-party code is bundled; it rejects malformed input with JsonError.
#ifndef LAYERED_SIM_MINIJSON_HH
#define LAYERED_SIM_MINIJSON_HH

#include <cstdlib>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace minijson {

struct JsonError : std::runtime_error {
  using std::runtime_error::runtime_error;
};

class Value {
 public:
  enum class Kind { Null, Bool, Number, String, Array, Object };
  Kind kind = Kind::Null;
  bool b = false;
  double num = 0.;
  std::string str;
  std::vector<Value> arr;
  std::map<std::string, Value> obj;

  bool isObject() const { return kind == Kind::Object; }
  bool isArray() const { return kind == Kind::Array; }
  bool isNumber() const { return kind == Kind::Number; }
  bool isString() const { return kind == Kind::String; }
  bool isBool() const { return kind == Kind::Bool; }
  bool has(const std::string& k) const { return isObject() && obj.count(k) > 0; }

  const Value& at(const std::string& k, const std::string& where) const {
    if (!isObject()) throw JsonError(where + ": expected an object");
    auto it = obj.find(k);
    if (it == obj.end()) throw JsonError(where + "." + k + " is required");
    return it->second;
  }
  double number(const std::string& where) const {
    if (!isNumber()) throw JsonError(where + " must be a number");
    return num;
  }
  const std::string& string(const std::string& where) const {
    if (!isString()) throw JsonError(where + " must be a string");
    return str;
  }
  bool boolean(const std::string& where) const {
    if (!isBool()) throw JsonError(where + " must be true or false");
    return b;
  }
  const std::vector<Value>& array(const std::string& where) const {
    if (!isArray()) throw JsonError(where + " must be an array");
    return arr;
  }
};

class Parser {
 public:
  explicit Parser(const std::string& text) : s_(text) {}
  Value parse() {
    Value v = value();
    ws();
    if (i_ != s_.size()) fail("trailing characters");
    return v;
  }

 private:
  const std::string& s_;
  std::size_t i_ = 0;

  [[noreturn]] void fail(const std::string& what) const {
    throw JsonError("JSON parse error at offset " + std::to_string(i_) + ": " + what);
  }
  void ws() {
    while (i_ < s_.size() && (s_[i_] == ' ' || s_[i_] == '\n' || s_[i_] == '\t' || s_[i_] == '\r')) ++i_;
  }
  bool lit(const char* word) {
    std::size_t n = std::char_traits<char>::length(word);
    if (s_.compare(i_, n, word) == 0) {
      i_ += n;
      return true;
    }
    return false;
  }
  Value value() {
    ws();
    if (i_ >= s_.size()) fail("unexpected end");
    Value v;
    char c = s_[i_];
    if (c == '{') {
      v.kind = Value::Kind::Object;
      ++i_;
      ws();
      if (i_ < s_.size() && s_[i_] == '}') {
        ++i_;
        return v;
      }
      while (true) {
        ws();
        if (i_ >= s_.size() || s_[i_] != '"') fail("expected a key");
        std::string k = string();
        ws();
        if (i_ >= s_.size() || s_[i_] != ':') fail("expected ':'");
        ++i_;
        if (v.obj.count(k)) fail("duplicate key " + k);
        v.obj[k] = value();
        ws();
        if (i_ < s_.size() && s_[i_] == ',') {
          ++i_;
          continue;
        }
        if (i_ < s_.size() && s_[i_] == '}') {
          ++i_;
          return v;
        }
        fail("expected ',' or '}'");
      }
    }
    if (c == '[') {
      v.kind = Value::Kind::Array;
      ++i_;
      ws();
      if (i_ < s_.size() && s_[i_] == ']') {
        ++i_;
        return v;
      }
      while (true) {
        v.arr.push_back(value());
        ws();
        if (i_ < s_.size() && s_[i_] == ',') {
          ++i_;
          continue;
        }
        if (i_ < s_.size() && s_[i_] == ']') {
          ++i_;
          return v;
        }
        fail("expected ',' or ']'");
      }
    }
    if (c == '"') {
      v.kind = Value::Kind::String;
      v.str = string();
      return v;
    }
    if (lit("true")) {
      v.kind = Value::Kind::Bool;
      v.b = true;
      return v;
    }
    if (lit("false")) {
      v.kind = Value::Kind::Bool;
      return v;
    }
    if (lit("null")) return v;
    const char* start = s_.c_str() + i_;
    char* end = nullptr;
    v.num = std::strtod(start, &end);
    if (end == start) fail("unexpected character");
    i_ += static_cast<std::size_t>(end - start);
    v.kind = Value::Kind::Number;
    return v;
  }
  unsigned hex4() {  // exactly four hex digits after \\u
    if (i_ + 4 > s_.size()) fail("bad \\u escape");
    unsigned code = 0;
    for (int k = 0; k < 4; ++k) {
      char h = s_[i_++];
      int d = (h >= '0' && h <= '9') ? h - '0' : (h >= 'a' && h <= 'f') ? h - 'a' + 10
            : (h >= 'A' && h <= 'F') ? h - 'A' + 10 : -1;
      if (d < 0) fail("bad \\u escape");
      code = code * 16 + static_cast<unsigned>(d);
    }
    return code;
  }
  static void utf8(unsigned code, std::string& out) {
    if (code < 0x80) {
      out += static_cast<char>(code);
    } else if (code < 0x800) {
      out += static_cast<char>(0xC0 | (code >> 6));
      out += static_cast<char>(0x80 | (code & 0x3F));
    } else if (code < 0x10000) {
      out += static_cast<char>(0xE0 | (code >> 12));
      out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
      out += static_cast<char>(0x80 | (code & 0x3F));
    } else {
      out += static_cast<char>(0xF0 | (code >> 18));
      out += static_cast<char>(0x80 | ((code >> 12) & 0x3F));
      out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
      out += static_cast<char>(0x80 | (code & 0x3F));
    }
  }
  std::string string() {
    ++i_;  // opening quote
    std::string out;
    while (i_ < s_.size() && s_[i_] != '"') {
      char c = s_[i_++];
      if (c == '\\') {
        if (i_ >= s_.size()) fail("bad escape");
        char e = s_[i_++];
        switch (e) {
          case '"': out += '"'; break;
          case '\\': out += '\\'; break;
          case '/': out += '/'; break;
          case 'n': out += '\n'; break;
          case 't': out += '\t'; break;
          case 'r': out += '\r'; break;
          case 'b': out += '\b'; break;
          case 'f': out += '\f'; break;
          case 'u': {  // any code point, as UTF-8; a surrogate pair is one code point, a lone surrogate an error
            unsigned code = hex4();
            if (code >= 0xDC00 && code <= 0xDFFF) fail("bad \\u escape: lone low surrogate");
            if (code >= 0xD800 && code <= 0xDBFF) {
              if (i_ + 2 > s_.size() || s_[i_] != '\\' || s_[i_ + 1] != 'u') fail("bad \\u escape: lone high surrogate");
              i_ += 2;
              unsigned low = hex4();
              if (low < 0xDC00 || low > 0xDFFF) fail("bad \\u escape: high surrogate without a low one");
              code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00);
            }
            utf8(code, out);
            break;
          }
          default: fail("bad escape");
        }
      } else {
        out += c;
      }
    }
    if (i_ >= s_.size()) fail("unterminated string");
    ++i_;
    return out;
  }
};

inline Value parse(const std::string& text) { return Parser(text).parse(); }

}  // namespace minijson

#endif
