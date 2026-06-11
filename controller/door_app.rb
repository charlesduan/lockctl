#!/usr/bin/env ruby

require 'yaml'
require 'socket'
require 'roda'
require 'tilt'
require 'webauthn'

#
# Manages connection to a door system. This class should be instantiated for
# each door as it is accessed.
#
class DoorManager

  #
  # Initialize a connection to a door. The parameter is a hash having keys
  # 'name', 'host', and 'port'.
  #
  def initialize(door)
    @door = door
    @socket = TCPSocket.open(door['host'], door['port'])
  end

  #
  # Send a single-line query to the door system and receive a single-line
  # response.
  #
  def query(command, *args)
    cmd = [ command, *args ].join(" ")
    @socket.puts(cmd)
    return @socket.gets.chomp
  end

  #
  # Sends a query to the door system and receives a multi-line response, per the
  # door system protocol. According to that protocol, the first received line is
  # the number of following response lines.
  #
  def multiline_query(command, *args)
    lines = query(command, *args).chomp.to_i
    return (1..lines).map { |i| @socket.gets.chomp }
  end

  #
  # Close the underlying socket connection to the door system.
  #
  def close
    @socket.close
  end

  #
  # Analogous to IO.open, creates a new DoorManager object and executes the
  # given block with the created object. The DoorManager is closed upon
  # completion.
  #
  def self.open(door)
    dm = self.new(door)
    return dm unless block_given?
    begin
      return yield(dm)
    ensure
      dm.close
    end
  end
end

class DoorApp < Roda

  plugin :render, engine: :haml
  plugin :h

  route do |r|

    @session = env['rack.session']

    r.root do
      view "index", locals: { name: @session[:name] }
    end

    r.on 'status' do
      display_status
    end

    r.on 'name', String do |str|
      @session[:name] = str
      render 'name', locals: { name: str }
    end

    r.on 'register' do
      route_register(r)
    end

  end

  def display_status
    res = {}
    opts[:config]['doors'].each do |door|
      begin
        res[door['name']] = DoorManager.open(door) { |dm| dm.query('status') }
      rescue
        res[door['name']] = "Error: #$!"
      end
    end
    view 'status', locals: { res: res }
  end

  def route_register(r)

    r.is do
      r.get do
        show_register_forms(r)
      end

      r.post do
        cred = WebAuthn::Credential.from_create(
          r.params['publicKeyCredential']
        )
        begin
          cred.verify(@session[:creation_challenge])
          @session.delete(:creation_challenge)
          @session[:webauthn_create] = {
            :id => cred.id,
            :key => cred.public_key,
            :count => cred.sign_count,
          }
          r.redirect "/register/success"
        rescue WebAuthn::Error => e
          # Handle verification error
        end
      end
    end

    r.is('name') do
      r.get do
      end

      r.post do
      end

    end

    r.is 'success' do
      render(
        'register-success', locals: {
          webauthn_create: @session[:webauthn_create]
        }
      )
    end
  end

  def show_register_forms(r)
    name = r.params['name']
    if name && name.is_a?(String) && !name.empty?
      user_id = WebAuthn.generate_user_id
      options = WebAuthn::Credential.options_for_create(
        user: {
          id: user_id,
          name: name.gsub(/\W+/, ' ').strip.gsub(/\W/, '-'),
          display_name: name,
        },
        authenticator_selection: {
          residentKey: 'required',
          userVerification: 'discouraged',
        },
      )

      @session[:creation_challenge] = options.challenge
      view(
        'register-challenge',
        locals: { options: options.as_json.to_json, name: name },
      )
    else
      view 'register'
    end
  end


end
