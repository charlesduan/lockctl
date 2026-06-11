require 'yaml'
require_relative 'door_app'
require 'rack/session'
require 'rack/protection'
require 'rack/reloader'
require 'webauthn'

app_config = YAML.load_file('config.yaml')

WebAuthn.configure do |config|
  # config.allowed_origins = app_config['allowed_origins']
  config.rp_name = app_config['name']
end

use Rack::Session::Pool, :expire_after => 60 * 60
use Rack::Protection
use Rack::Reloader

DoorApp.opts[:config] = app_config
run DoorApp.app
