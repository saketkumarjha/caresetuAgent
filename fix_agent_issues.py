#!/usr/bin/env python3
"""
Troubleshooting script to fix common voice agent issues.
This script will help identify and resolve:
1. Cartesia TTS billing issues (402 Payment Required)
2. LiveKit connection problems
3. API key validation
4. Environment configuration
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any
import aiohttp
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentTroubleshooter:
    """Troubleshoot and fix common voice agent issues."""
    
    def __init__(self):
        """Initialize troubleshooter."""
        self.issues_found = []
        self.fixes_applied = []
        
    def load_env_config(self) -> Dict[str, Any]:
        """Load and validate environment configuration."""
        logger.info("🔍 Loading environment configuration...")
        
        # Try to load from .env file
        env_vars = {}
        try:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                logger.info("✅ .env file loaded successfully")
            else:
                logger.warning("⚠️ .env file not found")
        except Exception as e:
            logger.error(f"❌ Error loading .env file: {e}")
        
        # Merge with system environment variables
        for key in ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 
                   'CARTESIA_API_KEY', 'ELEVENLABS_API_KEY', 'GOOGLE_API_KEY', 
                   'ASSEMBLYAI_API_KEY']:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        
        return env_vars
    
    async def check_cartesia_api(self, api_key: str) -> Dict[str, Any]:
        """Check Cartesia API status and billing."""
        logger.info("🔍 Checking Cartesia API status...")
        
        if not api_key or not api_key.startswith('sk_car_'):
            return {
                'status': 'invalid_key',
                'message': 'Invalid or missing Cartesia API key',
                'recommendation': 'Update CARTESIA_API_KEY in .env file'
            }
        
        try:
            # Test API endpoint
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                
                # Try to get account info or models (adjust endpoint as needed)
                async with session.get(
                    'https://api.cartesia.ai/models',  # Example endpoint
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        return {
                            'status': 'active',
                            'message': 'Cartesia API is working correctly',
                            'recommendation': None
                        }
                    elif response.status == 402:
                        return {
                            'status': 'payment_required',
                            'message': 'Cartesia API billing issue - payment required',
                            'recommendation': 'Check your Cartesia account billing status or use alternative TTS'
                        }
                    elif response.status == 401:
                        return {
                            'status': 'unauthorized',
                            'message': 'Cartesia API key is invalid or expired',
                            'recommendation': 'Update CARTESIA_API_KEY with a valid key'
                        }
                    else:
                        return {
                            'status': 'error',
                            'message': f'Cartesia API returned status {response.status}',
                            'recommendation': 'Check Cartesia API documentation'
                        }
        
        except asyncio.TimeoutError:
            return {
                'status': 'timeout',
                'message': 'Cartesia API request timed out',
                'recommendation': 'Check internet connection or try again later'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error checking Cartesia API: {e}',
                'recommendation': 'Check network connection and API key'
            }
    
    async def check_livekit_connection(self, url: str, api_key: str, api_secret: str) -> Dict[str, Any]:
        """Check LiveKit connection and credentials."""
        logger.info("🔍 Checking LiveKit connection...")
        
        if not all([url, api_key, api_secret]):
            return {
                'status': 'missing_credentials',
                'message': 'Missing LiveKit credentials',
                'recommendation': 'Check LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in .env'
            }
        
        try:
            # Basic URL validation
            if not url.startswith(('ws://', 'wss://')):
                return {
                    'status': 'invalid_url',
                    'message': 'LiveKit URL should start with ws:// or wss://',
                    'recommendation': 'Update LIVEKIT_URL format'
                }
            
            # Try to connect (simplified check)
            async with aiohttp.ClientSession() as session:
                # Convert WebSocket URL to HTTP for basic connectivity test
                http_url = url.replace('wss://', 'https://').replace('ws://', 'http://')
                
                try:
                    async with session.get(http_url, timeout=10) as response:
                        # Any response (even error) means the server is reachable
                        return {
                            'status': 'reachable',
                            'message': 'LiveKit server is reachable',
                            'recommendation': None
                        }
                except aiohttp.ClientConnectorError:
                    return {
                        'status': 'unreachable',
                        'message': 'Cannot reach LiveKit server',
                        'recommendation': 'Check LIVEKIT_URL and network connection'
                    }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error checking LiveKit: {e}',
                'recommendation': 'Verify LiveKit configuration'
            }
    
    async def check_google_api(self, api_key: str) -> Dict[str, Any]:
        """Check Google API status."""
        logger.info("🔍 Checking Google API status...")
        
        if not api_key:
            return {
                'status': 'missing_key',
                'message': 'Missing Google API key',
                'recommendation': 'Set GOOGLE_API_KEY in .env file'
            }
        
        try:
            # Simple validation - Google API keys typically start with 'AIza'
            if not api_key.startswith('AIza'):
                return {
                    'status': 'invalid_format',
                    'message': 'Google API key format appears invalid',
                    'recommendation': 'Verify GOOGLE_API_KEY format'
                }
            
            return {
                'status': 'format_valid',
                'message': 'Google API key format appears valid',
                'recommendation': 'Test with actual API call if issues persist'
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error checking Google API: {e}',
                'recommendation': 'Verify Google API key'
            }
    
    def create_fixed_env_file(self, env_vars: Dict[str, Any]) -> None:
        """Create a fixed .env file with working configuration."""
        logger.info("🔧 Creating fixed .env configuration...")
        
        # Template for working configuration
        fixed_config = f"""# LiveKit Cloud Configuration
LIVEKIT_URL={env_vars.get('LIVEKIT_URL', 'wss://assemblyaiproject-2oo3ntng.livekit.cloud')}
LIVEKIT_API_KEY={env_vars.get('LIVEKIT_API_KEY', 'APIG5xywiyjDmBu')}
LIVEKIT_API_SECRET={env_vars.get('LIVEKIT_API_SECRET', 'R5izbUJsSFu9rFtsslQDCQQcaEmciou1Xb8ZJRceenm')}

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY={env_vars.get('ASSEMBLYAI_API_KEY', '875312e8bf3240ee9e3e1890b15c217e')}

# Google Gemini Configuration
GOOGLE_API_KEY={env_vars.get('GOOGLE_API_KEY', 'AIzaSyA2YhBWNIjLzTep_3HDJhZyJdaGhTmED2M')}

# Cartesia TTS Configuration (DISABLED due to billing issues)
# CARTESIA_API_KEY=sk_car_kzUZ2jcUyUziozLd9HtqsL

# ElevenLabs Configuration (optional fallback TTS)
ELEVENLABS_API_KEY={env_vars.get('ELEVENLABS_API_KEY', 'ELEVENLABS_API_KEY')}

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/voice_agent
REDIS_URL=redis://localhost:6379

# External Service APIs
CRM_API_URL=https://your-crm-api.com
CRM_API_KEY=your-crm-api-key
CALENDAR_API_URL=https://your-calendar-api.com
"""
        
        # Backup existing .env file
        if os.path.exists('.env'):
            os.rename('.env', '.env.backup')
            logger.info("📁 Backed up existing .env to .env.backup")
        
        # Write fixed configuration
        with open('.env', 'w') as f:
            f.write(fixed_config)
        
        logger.info("✅ Created fixed .env configuration")
        self.fixes_applied.append("Created fixed .env configuration with Cartesia disabled")
    
    def create_troubleshooting_report(self) -> str:
        """Create a troubleshooting report."""
        report = f"""
🔧 VOICE AGENT TROUBLESHOOTING REPORT
=====================================

Issues Found:
{chr(10).join(f"- {issue}" for issue in self.issues_found) if self.issues_found else "- No major issues detected"}

Fixes Applied:
{chr(10).join(f"- {fix}" for fix in self.fixes_applied) if self.fixes_applied else "- No fixes needed"}

RECOMMENDATIONS:
1. Use Google TTS as primary (most reliable and free)
2. Disable Cartesia TTS until billing is resolved
3. Ensure stable internet connection for LiveKit
4. Monitor API usage to avoid rate limits

NEXT STEPS:
1. Run the agent with: python agent.py
2. Monitor logs for any remaining issues
3. Test voice functionality in LiveKit room
4. Contact support if issues persist

Generated: {asyncio.get_event_loop().time()}
"""
        return report
    
    async def run_full_diagnosis(self) -> None:
        """Run complete diagnosis and fix common issues."""
        logger.info("🚀 Starting voice agent troubleshooting...")
        
        # Load configuration
        env_vars = self.load_env_config()
        
        # Check Cartesia API (main issue)
        cartesia_result = await self.check_cartesia_api(env_vars.get('CARTESIA_API_KEY', ''))
        if cartesia_result['status'] == 'payment_required':
            self.issues_found.append(f"Cartesia TTS: {cartesia_result['message']}")
            logger.warning(f"⚠️ {cartesia_result['message']}")
        
        # Check LiveKit connection
        livekit_result = await self.check_livekit_connection(
            env_vars.get('LIVEKIT_URL', ''),
            env_vars.get('LIVEKIT_API_KEY', ''),
            env_vars.get('LIVEKIT_API_SECRET', '')
        )
        if livekit_result['status'] not in ['reachable']:
            self.issues_found.append(f"LiveKit: {livekit_result['message']}")
            logger.warning(f"⚠️ {livekit_result['message']}")
        
        # Check Google API
        google_result = await self.check_google_api(env_vars.get('GOOGLE_API_KEY', ''))
        if google_result['status'] not in ['format_valid']:
            self.issues_found.append(f"Google API: {google_result['message']}")
        
        # Apply fixes only if there are actual issues (not just payment_required which is now resolved)
        if any('Cartesia' in issue and 'payment_required' not in issue for issue in self.issues_found):
            self.create_fixed_env_file(env_vars)
        
        # Generate report
        report = self.create_troubleshooting_report()
        
        # Save report
        with open('troubleshooting_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        logger.info("✅ Troubleshooting completed. Check troubleshooting_report.txt for details.")

async def main():
    """Main function to run troubleshooting."""
    troubleshooter = AgentTroubleshooter()
    await troubleshooter.run_full_diagnosis()

if __name__ == "__main__":
    asyncio.run(main())