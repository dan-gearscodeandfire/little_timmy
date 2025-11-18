#!/usr/bin/env python3
"""
test_connectivity.py - Test connectivity to all required services
This script tests the network connectivity to all services required by the preprocessor
"""

import socket
import requests
import time
import sys
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class ServiceTest:
    name: str
    host: str
    port: int
    protocol: str = "tcp"
    endpoint: str = ""
    expected_response: str = ""
    timeout: int = 5

class ConnectivityTester:
    def __init__(self):
        self.services = [
            ServiceTest(
                name="Ollama LLM Server",
                host="windows-host",
                port=11434,
                endpoint="/api/generate",
                timeout=10
            ),
            ServiceTest(
                name="STT Server",
                host="windows-host",
                port=8888,
                endpoint="/health",
                timeout=5
            ),
            ServiceTest(
                name="TTS Server",
                host="tts-server",
                port=5000,
                endpoint="/",
                timeout=5
            ),
            ServiceTest(
                name="Motor Controller",
                host="motor-raspi",
                port=8080,
                endpoint="/health",
                timeout=5
            ),
            ServiceTest(
                name="PostgreSQL Database",
                host="localhost",
                port=5433,
                timeout=3
            )
        ]
    
    def print_header(self):
        print("=" * 60)
        print("           WSL Preprocessor Connectivity Test")
        print("=" * 60)
        print()
    
    def print_colored(self, text: str, color: str = "white"):
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "reset": "\033[0m"
        }
        print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")
    
    def test_tcp_connection(self, service: ServiceTest) -> Tuple[bool, str]:
        """Test basic TCP connection to a service"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(service.timeout)
            result = sock.connect_ex((service.host, service.port))
            sock.close()
            
            if result == 0:
                return True, f"TCP connection successful to {service.host}:{service.port}"
            else:
                return False, f"TCP connection failed to {service.host}:{service.port}"
        except socket.gaierror as e:
            return False, f"DNS resolution failed for {service.host}: {e}"
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def test_http_endpoint(self, service: ServiceTest) -> Tuple[bool, str]:
        """Test HTTP endpoint if available"""
        if not service.endpoint:
            return True, "No HTTP endpoint to test"
        
        try:
            url = f"http://{service.host}:{service.port}{service.endpoint}"
            response = requests.get(url, timeout=service.timeout)
            
            if response.status_code == 200:
                return True, f"HTTP endpoint responded with 200 OK"
            else:
                return False, f"HTTP endpoint responded with {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "HTTP connection refused"
        except requests.exceptions.Timeout:
            return False, "HTTP request timed out"
        except Exception as e:
            return False, f"HTTP error: {e}"
    
    def test_ollama_api(self, service: ServiceTest) -> Tuple[bool, str]:
        """Test Ollama API specifically"""
        if service.name != "Ollama LLM Server":
            return True, "Not Ollama service"
        
        try:
            url = f"http://{service.host}:{service.port}/api/generate"
            payload = {
                "model": "llama3.2:3b-instruct-q4_K_M",
                "prompt": "Test",
                "stream": False,
                "options": {"num_ctx": 512}
            }
            
            response = requests.post(url, json=payload, timeout=service.timeout)
            
            if response.status_code == 200:
                return True, "Ollama API responded successfully"
            else:
                return False, f"Ollama API responded with {response.status_code}"
        except Exception as e:
            return False, f"Ollama API error: {e}"
    
    def test_database_connection(self, service: ServiceTest) -> Tuple[bool, str]:
        """Test PostgreSQL database connection"""
        if service.name != "PostgreSQL Database":
            return True, "Not database service"
        
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=service.host,
                port=service.port,
                database="timmy_memory_v16",
                user="postgres",
                password="timmy_postgres_pwd",
                connect_timeout=service.timeout
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                return True, "Database connection and query successful"
            else:
                return False, "Database query failed"
        except ImportError:
            return False, "psycopg2 not installed (pip install psycopg2-binary)"
        except Exception as e:
            return False, f"Database error: {e}"
    
    def test_service(self, service: ServiceTest) -> Dict:
        """Test a single service comprehensively"""
        results = {
            "service": service.name,
            "host": service.host,
            "port": service.port,
            "tests": {},
            "overall_status": "unknown"
        }
        
        # Test TCP connection
        tcp_success, tcp_message = self.test_tcp_connection(service)
        results["tests"]["tcp"] = {"success": tcp_success, "message": tcp_message}
        
        if tcp_success:
            # Test HTTP endpoint if available
            http_success, http_message = self.test_http_endpoint(service)
            results["tests"]["http"] = {"success": http_success, "message": http_message}
            
            # Test specific service functionality
            if service.name == "Ollama LLM Server":
                ollama_success, ollama_message = self.test_ollama_api(service)
                results["tests"]["ollama_api"] = {"success": ollama_success, "message": ollama_message}
            elif service.name == "PostgreSQL Database":
                db_success, db_message = self.test_database_connection(service)
                results["tests"]["database"] = {"success": db_success, "message": db_message}
        
        # Determine overall status
        all_tests_passed = all(test["success"] for test in results["tests"].values())
        results["overall_status"] = "pass" if all_tests_passed else "fail"
        
        return results
    
    def test_all_services(self, parallel: bool = True) -> List[Dict]:
        """Test all services, optionally in parallel"""
        if parallel:
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_service = {executor.submit(self.test_service, service): service for service in self.services}
                results = []
                for future in as_completed(future_to_service):
                    results.append(future.result())
                return sorted(results, key=lambda x: x["service"])
        else:
            return [self.test_service(service) for service in self.services]
    
    def print_results(self, results: List[Dict]):
        """Print test results in a formatted way"""
        print("\nTest Results:")
        print("-" * 60)
        
        passed = 0
        failed = 0
        
        for result in results:
            status_color = "green" if result["overall_status"] == "pass" else "red"
            status_symbol = "✓" if result["overall_status"] == "pass" else "✗"
            
            self.print_colored(f"{status_symbol} {result['service']} ({result['host']}:{result['port']})", status_color)
            
            for test_name, test_result in result["tests"].items():
                test_color = "green" if test_result["success"] else "red"
                test_symbol = "  ✓" if test_result["success"] else "  ✗"
                self.print_colored(f"{test_symbol} {test_name.upper()}: {test_result['message']}", test_color)
            
            print()
            
            if result["overall_status"] == "pass":
                passed += 1
            else:
                failed += 1
        
        print("-" * 60)
        self.print_colored(f"Summary: {passed} passed, {failed} failed", "cyan")
        
        if failed > 0:
            print()
            self.print_colored("⚠️  Some services are not reachable. Check the following:", "yellow")
            self.print_colored("   1. Run the PowerShell setup script as Administrator", "yellow")
            self.print_colored("   2. Ensure all services are running on their respective hosts", "yellow")
            self.print_colored("   3. Check firewall settings", "yellow")
            self.print_colored("   4. Verify network connectivity", "yellow")
        else:
            self.print_colored("🎉 All services are reachable!", "green")
    
    def export_results(self, results: List[Dict], filename: str = "connectivity_report.json"):
        """Export results to JSON file"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "summary": {
                "total_services": len(results),
                "passed": len([r for r in results if r["overall_status"] == "pass"]),
                "failed": len([r for r in results if r["overall_status"] == "fail"])
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {filename}")

def main():
    tester = ConnectivityTester()
    tester.print_header()
    
    # Parse command line arguments
    parallel = True
    export_report = False
    
    if len(sys.argv) > 1:
        if "--sequential" in sys.argv:
            parallel = False
        if "--export" in sys.argv:
            export_report = True
    
    print("Testing connectivity to all required services...")
    if parallel:
        print("Running tests in parallel...")
    else:
        print("Running tests sequentially...")
    
    print()
    
    # Run tests
    start_time = time.time()
    results = tester.test_all_services(parallel=parallel)
    end_time = time.time()
    
    # Print results
    tester.print_results(results)
    print(f"\nTest completed in {end_time - start_time:.2f} seconds")
    
    # Export report if requested
    if export_report:
        tester.export_results(results)
    
    # Exit with appropriate code
    failed_count = len([r for r in results if r["overall_status"] == "fail"])
    sys.exit(0 if failed_count == 0 else 1)

if __name__ == "__main__":
    main() 