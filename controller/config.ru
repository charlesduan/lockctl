require 'yaml'
require_relative 'door_app'
require 'rack/session'
require 'rack/protection'

use Rack::Session::Pool, :expire_after => 60 * 60
use Rack::Protection

DoorApp.opts[:config] = YAML.load_file('config.yaml')
run DoorApp.freeze.app
